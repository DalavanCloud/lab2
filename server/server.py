#import zerorpc
import time
import threading
import csv
import random
import xmlrpclib 
import SimpleXMLRPCServer
import sys
sys.path.append("./")
import setting
import multicast
import select
import socket

#class for Gateway
class Gateway(object):
	#initial class
    def __init__(self,sadd,devNum):
        #connect to db
        self._isLeader = 0
        self._electID = random.random()
        self._timeoffset = 0
        self._n = 1 #number of registered devices
        self._idlist = [["gateway","gateway",sadd,0]]#list for registered devices
        self._mode = "HOME"
        self.serveradd = sadd #server address
        self._idx = {} #index for global id
        self.lasttime = -1 #last time the motion sensor was on
        self.log = open("server_log.txt",'w+') #server log file
        self.cid = 0
        self.vector = [0] * devNum 

    def leader_elect(self):
        elect_list = ["server"]
        elect_dict = {"server":('', setting.eleport)}
        elt_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        elt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        elt_socket.bind(('', setting.eleport))
        n = 1
        while n<setting.devNum:
            print "Listening"
            recv_data, addr = elt_socket.recvfrom(2048)
            print recv_data,addr
            if recv_data not in elect_list:
                elect_list.append(recv_data)
                elect_dict[recv_data] = addr
                n = n+1
        for k in range(1,n):
            elt_socket.sendto(str(elect_dict[elect_list[(k+1)%n]]),elect_dict[elect_list[k]])
        #elt.socket.sendto(
        msg = "ele#"+str(self._electID)
        elt_socket.sendto(msg,elect_dict[elect_list[1]])
        recv_data, addr = elt_socket.recvfrom(2048)
        ld = -1
        print recv_data,addr
        eidlist = recv_data.split("#")
        if eidlist[0] == "ele":
            eidlist = eidlist[1:]
            maxid = -1
            for i in range(n):
               if float(eidlist[i])>maxid:
                   maxid = float(eidlist[i])
                   ld = i
        if ld == 0:
            self._isLeader = 1
        for i in range(1,n):
            if ld == i:
                elt_socket.sendto("1",elect_dict[elect_list[i]])
            else:
                elt_socket.sendto("0",elect_dict[elect_list[i]])
        print "server ",self._electID,self._isLeader 
        return 1
            
    def time_syn(self):
        if self._isLeader == 1:
    	    connect_list = []
            syn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            syn_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            syn_socket.bind(("127.0.0.1", setting.synport))
            syn_socket.listen(8)
        #print "server listen"
            while len(connect_list) < setting.devNum-1:
                sockfd, addr = syn_socket.accept()
                print addr
                connect_list.append(sockfd)
            #print "server send"
            for sk in connect_list:
                sk.send(str(time.time()))
            offsets = []
            ready = []
        #print "server receive"
            while len(offsets)< setting.devNum-1:#setting.devNum-1
                read_sockets,write_sockets,error_sockets = select.select(connect_list,[],[])
                for sk in read_sockets:
                    if sk not in ready:
                        of = sk.recv(1024)
                        offsets.append(float(of))
                        ready.append(sk)   
            moffset = sum(offsets)/(len(offsets)+1.0)
            for sk in connect_list:
                sk.send(str(moffset))
            self._timeoffset = moffset
            syn_socket.close()    
        #print "server ",moffset
        else: 
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            time.sleep(1+random.random())
            s.connect(("127.0.0.1",setting.synport))
            mt = s.recv(1024)
            offset = time.time()+3.0-float(mt)
        #time.sleep(3*random.random())
            s.send(str(offset))
            moffset = s.recv(1024)
        #print "User ",mt,offset,moffset
            self._timeoffset = float(moffset) - offset
            s.close()
        
    # thread for server listening
    def start_listen(self):
        self.s = SimpleXMLRPCServer.SimpleXMLRPCServer(self.serveradd,logRequests=False)#zerorpc.Server(self)
        self.s.register_instance(self)#self.s.bind(self.serveradd)
        self.s.serve_forever()#self.s.run()
    
    #rpc call for query state
    def query_state(self,id):
    	# checking invalidate id
        if id >= self._n:
            print "Wrong Id"
            return -1
        #set up connection
        c = xmlrpclib.ServerProxy(self._idlist[id][2],verbose=0) #zerorpc.Client()
        #c.connect(self._idlist[id][2])
        #rpc call
        multicast.multicast(self.serveradd, self.vector)
        state = c.query_state()
        #c.close()
        timestmp = round(time.time()+self._timeoffset-setting.start_time,2)
        self.writedb(id,state,timestmp,self.vector)
        self._idlist[id][3] = state
        #log
        self.log.write(str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n')
        print str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n'
        #record the last time motion sensor was on 
        if self._idlist[id][1] == "motion" and state == '1':
            self.lasttime = time.time()
        return state
        
    def writedb(self,id,state,timestmp,vector):
        c = xmlrpclib.ServerProxy("http://"+setting.Dbadd[0]+":"+str(setting.Dbadd[1]),verbose=0)
        print "#$#$#$#"
        c.write(id,state,timestmp,vector)
        print "####"
        return 1
        
    def readdb(self,id,timestmp):
        c = xmlrpclib.ServerProxy("http://"+setting.Dbadd[0]+":"+str(setting.Dbadd[1]),verbose=0)
        c.read(id,timestmp)
        return 1
        
    #rpc interface for report state
    def report_state(self, id, state):
    	#checking invalidate id
    	print "Server ",id,state
        if id >= self._n:
            print "Wrong Id"
            return -1
        timestmp = round(time.time()+self._timeoffset-setting.start_time,2)
        self.writedb(id,state,timestmp,self.vector)
        self._idlist[id][3] = state
        #log
        self.log.write(str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n')
        print str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n'
    	#task 2
        if self._idlist[id][1] == "motion":
        	#home mode turn on bulb if there is motion
            print server._mode
            if server._mode == "HOME":
                if "bulb" not in server._idx:
                    print "No bulb"
                    return 1
                if state == '1':
                    self.lasttime = time.time()
                    self.change_state(self._idx["bulb"],1)
                else:
                    if self.lasttime != -1 and time.time()-self.lasttime> 5:
                        self.change_state(self._idx["bulb"],0)
            #away mode set message if there is motion
            else:
                if state == '1':
                    print "Server: Someone in your room!"
                    self.text_message("Someone in your room!")
        return 1
        
    #rpc call for change state    
    def change_state(self, id, state):
    	#checking invalidate id
        if id >= self._n:
            print "Wrong Id"
            return -1
        #set up connection
        #c = zerorpc.Client()
        #rpc call
        c = xmlrpclib.ServerProxy(self._idlist[id][2],verbose=0)
        #c.connect(self._idlist[id][2])
        flag = 0

        multicast.multicast(self.serveradd, self.vector)
        if c.change_state(state):
            flag = 1
        #c.close()
        return flag
    
    #rpc interface for register
    def register(self,type,name,address):
    	#register device
        self._idlist.append([type,name,"http://"+address[0]+":"+str(address[1]),0])
        #assign global id
        self._idx[name] = self._n
        #increase number of registed device
        self._n =self._n + 1
        #log
        self.log.write(str(round(time.time()-setting.start_time,2))+','+name+','+str(self._n - 1)+'\n')
        print str(round(time.time()-setting.start_time,2))+','+name+','+str(self._n - 1)+'\n'
        #return global id
        return self._n - 1
    
    #rpc call for text message    
    def text_message(self,msg):
    	#checking invalidate id
        if "user" not in self._idx:
            print "No user process"
            return
        #set up connection
        c = xmlrpclib.ServerProxy(self._idlist[self._idx["user"]][2],verbose=0)#zerorpc.Client()
        #rpc call
        #c.connect(self._idlist[self._idx["user"]][2])
        c.text_message(str(round(time.time()-setting.start_time,2))+","+msg)
        #c.close()
        
    #rpc interface for change mode
    def change_mode(self,mode):
    	#print mode
        self._mode = mode
        return self._mode

    def  update_vector_clock(self,vector):
        for i in range(len(vector)):
            if vector[i] > self.vector[i]:
                self.vector[i] = vector[i]

        self.vector[self.cid] = self.vector[self.cid]+1
        return 1
		
#thread for listening
class myserver(threading.Thread):
    def __init__(self,server):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.server = server
    def run(self):
        self.server.start_listen()

#read certain column in test case file
def readTest(filename,col):		
       with open(filename, 'rb') as csvfile:
           spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
           time=[]
           action=[]
           spamreader.next()
           for row in spamreader:
               time.append(row[0])
               action.append(row[col])     
           return time, action


timel,action = readTest('test-input.csv',5)

devNum = setting.devNum 
server = Gateway(setting.serveradd,devNum)
server.leader_elect()
server.time_syn()
listen_thread = myserver(server)
listen_thread.start()


#calcuate start time
current_time = int(time.time())
waitT = setting.start_time - current_time
time.sleep(waitT)
time.sleep(3)
#server.text_msg("Someone in your room!")

for index in range(len(timel)):
    at = action[index].split(';')
    
    #query temperature sensor
    if  'Q(Temp)' in at:
        if "temperature" not in server._idx:
            print "No temperature sensor"
            continue
        tem = server.query_state(server._idx["temperature"])
        if "outlet" not in server._idx:
            print "No outlet"
            continue
        #print "temperature ",tem
        if int(tem) < 1:
            server.change_state(server._idx["outlet"],1)
        elif int(tem) >= 2:
            server.change_state(server._idx["outlet"],0)
    #query motion sensor
    if  'Q(Motion)' in at:
        if "motion" not in server._idx:
            print "No montion sensor"
            continue
        mo = server.query_state(server._idx["motion"])
        if server._mode == "HOME":
            if "bulb" not in server._idx:
                print "No bulb"
                continue
            if server._idlist[server._idx["motion"]][3] == '1':
                server.change_state(server._idx["bulb"],1)
            else:
                if time.time()-server.lasttime> 5:
                    server.change_state(server._idx["bulb"],0)
        else:
            if server._idlist[server._idx["motion"]][3] == '1':
                server.text_message("Someone in your room!")
    
    if index+1<len(timel):
        waitTime = float(timel[index+1])+float(setting.start_time) - time.time()+random.random()/50.0
        #print "wt: ",waitTime
        if waitTime>0:
            time.sleep(waitTime)




