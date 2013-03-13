import twitter
import credentials
import time
import shelve
import math
import signal
import sys
from twitter import Twitter, OAuth, TwitterHTTPError
from httplib import IncompleteRead

sh = shelve.open('twits_shelf.db',writeback=True)
keys=['followers','names','distance','userobject']

for key in keys:
    if key not in sh:
        sh[key]={}

followers = sh['followers']
names = sh['names']
distance = sh['distance']
pending = set()
userobject = sh['userobject']

t = Twitter(auth=OAuth(credentials.ACCESS_TOKEN,
    credentials.ACCESS_TOKEN_SECRET,
    credentials.CONSUMER_KEY,
    credentials.CONSUMER_SECRET))

creds = t.account.verify_credentials()
myid = creds['id']
names[myid] = creds['screen_name']
distance[myid] = 0
pending.add(myid)

def getinfo(piece):
    piecestr = ",".join(map(str,piece)) if type(piece) != str and len(piece)>1 else piece[0]
    look=t.users.lookup(user_id=piecestr)
    retrievedids=[]
    for ob in look:
        uid=ob['id']
        userobject[uid]=ob
        retrievedids.append(uid)
    print "Got info for %s" % repr(piece)
    if type(piece) != int:
        print "Total: %s" % len(piece) 
        print "Difference: %s" % [person for person in piece if person not in retrievedids]
    else:
        print "Total: 1" 

def explore_user(t,uid):
    print "Exploring uid %s" % uid
    newdist = distance[uid]+ 1
    try:
        follos = t.followers.ids(user_id=uid)['ids']
    except TwitterHTTPError as ex:
        print "Error code %s" % ex.e.code 
        if ex.e.code == 401: # Private Twitter
            return
        raise ex
    followers[uid]=follos
    for follo in follos:
        if follo not in followers.keys():
            pending.add(follo)
        distance[follo] = newdist

while True:
    try:
        print "Iteration!"
        nextuser=None
        minimumscore=1000
        unknowns = [person for person in pending if person not in userobject]
        for i in xrange(0,int(math.ceil(len(unknowns)/100))):
            piece = unknowns[i*100:(i+1)*100]
            getinfo(piece)
        for user in pending.copy():
            userscore = userobject[user]['followers_count']**distance[user]
            if(userscore < minimumscore):
                minimumscore = userscore
                nextuser=user
            explore_user(t,pending.pop())
    except TwitterHTTPError as ex:
        print "Exception %s - %s" % (ex,type(ex))
        if ex.e.code/10 == 42:
            print "Sleeping for 1 minute"
            time.sleep(60)
    except IncompleteRead:
        print "IncompleteRead!"
        time.sleep(5)

