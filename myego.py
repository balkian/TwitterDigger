import twitter
import credentials
import time
import shelve
import math
import signal
import sys
import argparse
import threading
from twitter import Twitter, OAuth, TwitterHTTPError
from httplib import IncompleteRead

class Fetcher(threading.Thread):
    def __init__(self, fname, credentials):
        self.t = Twitter(auth=OAuth(credentials.ACCESS_TOKEN,
            credentials.ACCESS_TOKEN_SECRET,
            credentials.CONSUMER_KEY,
            credentials.CONSUMER_SECRET))
        self.fname=fname
        threading.Thread.__init__(self)

    def run(self):
        while True:
            timetowait = 0
            try:
                lock.acquire()
                print "Iteration! for Fetcher %s" % self.fname
                nextuser=None
                minimumscore=1000
                unknowns = [person for person in pending if person not in userobject]
                for i in xrange(0,int(math.ceil(len(unknowns)/100.0))):
                    piece = unknowns[i*100:(i+1)*100]
                    self.getinfo(piece)
                for user in pending.copy():
                    userscore = userobject[user]['followers_count']**distance[user]
                    if(userscore < minimumscore):
                        minimumscore = userscore
                        nextuser=user
                self.explore_user(nextuser)
                pending.remove(nextuser)
                sh.sync()
                timetowait = 5
            except TwitterHTTPError as ex:
                print "Exception %s - %s" % (ex,type(ex))
                if ex.e.code/10 == 42:
                    print "Sleeping for 1 minute"
                    timetowait = 60
            except IncompleteRead:
                print "IncompleteRead!"
                timetowait = 5
            except Exception as ex:
                print "Exception"
                raise ex
            finally:
                lock.release()
                if timetowait:
                    time.sleep(timetowait)

    def getinfo(self,piece):
        piecestr = ",".join(map(str,piece)) if type(piece) != str and len(piece)>1 else piece[0]
        look=self.t.users.lookup(user_id=piecestr)
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

    def explore_user(self,uid):
        t = self.t
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get an ego network for a given ID.')

    parser.add_argument('NAME', nargs='?', metavar='id',
            default='me', type=str, help='Name of the user to be used as a center')

    parser.add_argument('--new','-n',action='store_true', help='Start a new search.')

    args = parser.parse_args()

    print args.new
    print args.NAME

    sh = shelve.open('twits_shelf-%s.db' % args.NAME,writeback=True)
    keys=['followers','distance','userobject']

    for key in keys:
        if key not in sh or args.new:
            sh[key]={}

    followers = sh['followers']
    distance = sh['distance']
    pending = set()
    userobject = sh['userobject']

    lock = threading.RLock()

    t = Twitter(auth=OAuth(credentials.ACCESS_TOKEN,
        credentials.ACCESS_TOKEN_SECRET,
        credentials.CONSUMER_KEY,
        credentials.CONSUMER_SECRET))

    if not args.new:
        print 'Recovering state.'
        for key in followers:
            for follower in followers[key]:
                if follower not in followers:
                    pending.add(follower)

    if args.new or len(pending)<1:
        if args.NAME != 'me':
            user = t.users.lookup(screen_name=args.NAME)[0]
            uid = user['id']
            distance[uid] = 0
            pending.add(uid)
        else:
            creds = t.account.verify_credentials()
            myid = creds['id']
            distance[myid]=0
            pending.add(myid)

    print 'Pending is now: %s' %pending

    def signal_handler(signal, frame):
            print 'You pressed Ctrl+C!'
            sh.close()
            sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    f1 = Fetcher('f1',credentials)
    f1.run()

