import zerorpc

import time

import threading

import csv

import random

import sys

sys.path.append("./")

import setting



#class for Gateway

class Gateway(object):

	#initial class
#*
    def __init__(self,sadd,devNum):

        self._n = 0 #number of registered devices

        self._idlist = []#list for registered devices

        self._mode = "HOME"

        self.serveradd = sadd #server address

        self._idx = {} #index for global id

        self.lasttime = -1 #last time the motion sensor was on

        self.log = open("server_log.txt",'w+') #server log file
#*
        self.vector = [0] * devNum

   

    # thread for server listening

    def start_listen(self):

        self.s = zerorpc.Server(self)

        self.s.bind(self.serveradd)

        self.s.run()

    

    #rpc call for query state

    def query_state(self,id):

    	# checking invalidate id

        if id >= self._n:

            print "Wrong Id"

            return -1

        #set up connection

        c = zerorpc.Client()

        c.connect(self._idlist[id][2])

        #rpc call

        state = c.query_state()

        c.close()

        self._idlist[id][3] = state

        #log

        self.log.write(str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n')

        print str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n'

        #record the last time motion sensor was on 

        if self._idlist[id][1] == "motion" and state == '1':

            self.lasttime = time.time()

        return state

    

    #rpc interface for report state

    def report_state(self, id, state):

    	#checking invalidate id

        if id >= self._n:

            print "Wrong Id"

            return -1

        self._idlist[id][3] = state

        #log

        self.log.write(str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n')

        print str(round(time.time()-setting.start_time,2))+','+self._idlist[id][1]+','+state+'\n'

    	#task 2

        if self._idlist[id][1] == "motion":

        	#home mode turn on bulb if there is motion

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

                    self.text_message("Someone in your room!")

        return 1

        

    #rpc call for change state    

    def change_state(self, id, state):

    	#checking invalidate id

        if id >= self._n:

            print "Wrong Id"

            return -1

        #set up connection

        c = zerorpc.Client()

        #rpc call

        c.connect(self._idlist[id][2])

        flag = 0

        if c.change_state(state):

            flag = 1

        c.close()

        return flag

    

    #rpc interface for register

    def register(self,type,name,address):

    	#register device

        self._idlist.append([type,name,address,0])

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

        c = zerorpc.Client()

        #rpc call

        c.connect(self._idlist[self._idx["user"]][2])

        c.text_message(str(round(time.time()-setting.start_time,2))+","+msg)

        c.close()

        

    #rpc interface for change mode

    def change_mode(self,mode):

        self._mode = mode



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





timel,action = readTest('test-input.csv',3)

server = Gateway(setting.serveradd)

listen_thread = myserver(server)

listen_thread.start()



#calcuate start time

current_time = int(time.time())

waitT = setting.start_time - current_time

time.sleep(waitT)



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

                server.text_massage("Someone in your room!")

    

    if index+1<len(timel):

        waitTime = float(timel[index+1])+float(setting.start_time) - time.time()+random.random()/50.0

        #print "wt: ",waitTime

        if waitTime>0:

            time.sleep(waitTime)











