# Synthesis of linear predictable cache coherence protocols

# Step 1: Analyze
# Step 2: Construct stable state protocol specification
# Step 3: Construct non-stalling protocol specification
# Step 4: Verify protocol (model checker)

import sys, getopt
import re
from graphviz import Digraph
from ctypes import c_char_p
import copy

# dictionaries for parsing
stateMap = {}
Id = 0

# list of events
E = ('OwnWriteM', 'OwnWriteP', 'OtherWrite', 'OwnReadM', 'OwnReadP', 'OtherRead', 'Replacement')

# list of actions
A = ('Send data', 'Write-back data', 'Broadcast message', 'Set owner')

# weighting functions
aweightMap = {"write":2, "exclusiveRead":2, "read":1, "invalid":0} # access permission weight
mweightMap = {"dirty":1, "clean":0} # shared memory weight
pweightMap = {"active":1, "passive":0} # peer weight

class CoherenceState:
    def __init__ (self, state, isStableState):
        self.state = state
        self.isStableState = isStableState
        self.AP = -1
        self.SMP = -1
        self.PCP = -1
        self.parent = None
        self.isPreOrdered = False 
        self.source = None
        self.intendedDest = None

    def isTransientState(self):
        return not self.isStableState

    def isStableState(self):
        return self.isStableState

    def copyStateEncoding(self, state):
        if (state.isTransientState()):
            if (state.getParent() == None):
                self.AP = state.source.AP
                self.SMP = state.source.SMP
                self.PCP = state.source.PCP
            else:
                self.AP = state.getParent().AP
                self.SMP = state.getParent().SMP
                self.PCP = state.getParent().PCP
        else:
            self.AP = state.AP
            self.SMP = state.SMP
            self.PCP = state.PCP

    def setParent(self, p):
        self.parent = p

    def setSource(self, s):
        self.source = s

    def setIntendedDestination(self, d):
        self.intendedDest = d

    def setAP(self, ap):
        self.AP = ap

    def setSMP(self, smp):
        self.SMP = smp

    def setPCP(self, pcp):
        self.PCP = pcp

    def setPreOrderedFlag(self):
        self.isPreOrdered = True

    def getAP(self):
        if (self.isTransientState()):
            if (self.getParent() == None):
                return self.source.AP
            return self.getParent().source.AP
        return self.AP
    
    def getSMP(self):
        if (self.isTransientState()):
            if (self.getParent() == None):
                return self.source.SMP
            return self.getParent().source.SMP
        return self.SMP

    def getPCP(self):
        if (self.isTransientState()):
            if (self.getParent() == None):
                return self.source.PCP
            return self.getParent().source.PCP
        return self.PCP

    def getStateString(self):
        return str(self.state)

    def getStateEncoding(self):
        if (self.isTransientState()):
            return (self.source.AP, self.source.SMP, self.source.PCP)
        return (self.AP, self.SMP, self.PCP)

    def getAPWeight(self):
        return aweightMap[self.AP]

    def getSMPWeight(self):
        return mweightMap[self.SMP]

    def getPCPWeight(self):
        return pweightMap[self.PCP]
 
    def getIntendedDestination(self):
        return self.intendedDest
 
    def getSource(self):
        if (self.getParent() == None):
            return self.source
        return self.getParent().source

    def getParent(self):
        return self.parent

    def printState(self):
        print ("State: "+str(self.state)+ " AP: "+str(self.AP) + " SM: "+str(self.SMP) + " PP: "+str(self.PCP))

class Transition:
    def __init__(self, source, event, destination):
        self.source = source
        self.destination = destination
        self.event = event
        self.stableSource = source
        self.stableDestination = destination
        self.action=''

        if (source.isTransientState()):
            self.stableSource = source.getSource()

        if (destination.isTransientState()):
            self.stableDestination = destination.getIntendedDestination()

    def getSource(self):
        return self.source

    def getDestination(self):
        return self.destination

    def getStableSource(self):
        return self.stableSource

    def getStableDestination(self):
        return self.stableDestination

    def getSourceDestinationPair(self):
        return (self.source, self.destination)

    def getTriggerEvent(self):
        return self.event

    def setAction(self, action):
        self.action = action

    def getAction(self):
        return self.action
    
    def updateTriggerEvent(self, e):
        self.event = e

    def printTransition(self):
        print(str(self.source.state)+" -- "+str(self.event)+" --> "+str(self.destination.state))


class StateView:
    def __init__(self, si, sj):
        self.si = si
        self.sj = sj

    def computeAPWeight(self):
        w = self.si.getAPWeight() + self.sj.getAPWeight()
        return w

    def computePPWeight(self):
        w = self.si.getPCPWeight() + self.sj.getPCPWeight()
        return w

    def computeSMWeight(self):
        w = self.si.getSMPWeight() + self.sj.getSMPWeight()
        return w

    def computeCacheWeight(self):
        w = self.si.getCacheWeight() + self.sj.getCacheWeight()
        return w

    def getState(self, Id):
        if (Id == 0):
            return self.si

        return self.sj

    def isCacheHit(self):
        if (self.si == self.sj):
            return True
        return False

    def printStateView(self):
        print(str(self.si.getStateString()+", "+self.sj.getStateString()))

    def isValid(self):
        if (self.si == 'NA' or self.sj == 'NA'):
            return False

        if (self.computeAPWeight() > 2):
            return False
        
        if (self.computePPWeight() > 1):
            return False

        return True

class CoherenceProtocol:
    def __init__(self):
        self.states = []
        self.memStates = []
        self.preOrderedStates = []
        self.postOrderedStates = []
        self.transitions = []
        self.memTransitions = []
        self.U = []
        self.linearTransitions = []
        self.nonLinearTransitions = []
        self.ipStates = []
        self.ipTransitions = []
        self.EV = [("OwnWriteM", "OtherWrite"), ("OwnWriteP", "OtherWrite"), ("OtherWrite", "OwnWriteM"), ("OtherWrite", "OwnWriteP"), ("OwnReadM", "OtherRead"), ("OwnReadP", "OtherRead"), ("OtherRead", "OwnReadM"), ("OtherRead", "OwnReadP")]


    def printProtocol(self):
        # print function
        print ("--- Protocol specification --- ")
        for t in self.transitions:
            t.printTransition()

    def visualizeProtocol(self):
        f = Digraph("Protocol visualization", filename = "private-cache-state-machine.viz")
        g = Digraph("Protocol visualization", filename = "shared-memory-state-machine.viz")

        f.attr(rankdir="LR", size="10,10")
        g.attr(rankdir="LR", size="10,10")

        f.attr('node', shape='circle')
        g.attr('node', shape='square')

        
        ff = open(str("output-private-cache.csv"), "a")
        gf = open(str("output-shared-memory.csv"), "a")

        ff.write("Source,Event,Action,Destination")
        gf.write("Source,Event,Action,Destination")

        for t in self.transitions:
            ff.write(str(t.getSource().getStateString())+","+str(t.getTriggerEvent())+","+str(t.getAction())+","+str(t.getDestination().getStateString())+"\n")

        for t in self.memTransitions:
            gf.write(str(t.getSource().getStateString())+","+str(t.getTriggerEvent())+","+str(t.getAction())+","+str(t.getDestination().getStateString())+"\n")

        ff.close()
        gf.close()
        
        for t in self.transitions:
            f.edge(str(t.getSource().getStateString()), str(t.getDestination().getStateString()), label=str(str(t.getTriggerEvent())+"/"+str(t.getAction())))

        for t in self.memTransitions:
            g.edge(str(t.getSource().getStateString()), str(t.getDestination().getStateString()), label=str(str(t.getTriggerEvent())+"/"+str(t.getAction())))

         
       # print ("Total transitions: "+str(len(self.transitions) + len(self.memTransitions)))

        #f.view()
        #g.view()
        f.render("private-cache-state-machine.viz", view=True)
        g.render("shared-memory-state-machine.viz", view=True)

    def getU(self):
        return self.U

    def isNonLinearLatency(self):
        if (len(self.nonLinearTransitions) > 0):
            return True
        return False

    def isExclusiveStateExists(self):
        for s in self.states:
            if (s.getAP() == "exclusiveRead"):
                return True
        return False

    def isForwardingStateExists(self):
        for s in self.states:
            if (s.getAP() == "read" and s.getPCP() == "active" and s.getSMP() == "clean"):
                return True
        return False

    def isExclusiveDirtyStateExists(self):
        for s in self.states:
            if (s.getAP() == "exclusiveRead" and s.getSMP() == "dirty"):
                return True
        return False

    def printNonLinearTransitions(self):
        for t in self.nonLinearTransitions:
            t.printTransition()
            #printStr = str(t[0].printStateView()+ " -- "+str(t[1])+" --> "+t[2].printStateView())
            #print (printStr)

    def addState(self, state):
        for s in self.states:
            if (s.state == state.state):
                return s
        self.states.append(state)
        return state

    def addMemState(self, state):
        self.memStates.append(state)

    def addPreOrderedState(self, state):
        for i in self.preOrderedStates:
            if (i.getStateString() == state.getStateString()):
                return i
        self.preOrderedStates.append(state)
        self.states.append(state)
        return state


    def addPostOrderedState(self, state):
        for i in self.postOrderedStates:
            if (i.getStateString() == state.getStateString()):
                return i 
        self.postOrderedStates.append(state)
        self.states.append(state)
        return state

    def addTransition(self, transition):
        for t in self.transitions:
            if (t.source.getStateString() == transition.source.getStateString() and 
                t.destination.getStateString() == transition.destination.getStateString() and
                t.event == transition.event):
                return
        
        self.transitions.append(transition)

    def addMemTransition(self, transition):
        for t in self.memTransitions:
            if (t.source.getStateString() == transition.source.getStateString() and
                    t.destination.getStateString() == transition.destination.getStateString() and
                    t.event == transition.event):
                return

        self.memTransitions.append(transition)

    def addNonLinearTransitions(self, a):
        self.nonLinearTransitions.append(a)

    def addLinearTransitions(self, a):
        self.linearTransitions.append(a)

    def constructU(self):
        for si in self.states:
            for sj in self.states:
                sv = StateView(si, sj)
                if (sv.isValid()):
                    self.U.append(sv)

    def getTransitionDestination(self, s, e):
        t = self.getIpTransition(s, e)
        if (t != None):
            return t.getStableDestination()


    def getTransition(self, s, e):
        for t in self.transitions:
            if (t.getSource() == s and t.getTriggerEvent() == e):
                return t

        return None
    
    def getIpTransition(self, s, e):
        for t in self.ipTransitions:
            if (t.getSource().getStateString() == s.getStateString() and t.getTriggerEvent() == e):
                return t
        return None

    
    def isSameState(self, s, t):
        if (s.getAPWeight() == t.getAPWeight() and s.getPCPWeight() == t.getPCPWeight() and s.getSMPWeight() == t.getSMPWeight()):
            return True
        return False

    def preOrderedTransitions(self, configModel):
        O = ["OtherRead", "OtherWrite"]
        for ts in self.preOrderedStates:
            for e in O:
                nextDest = self.getTransitionDestination(ts.getSource(), e)

                if (self.isSameState(nextDest, ts)):
                    t = Transition(ts, e, ts)
                    self.addTransition(t)
                else:
                    if (ts.getSource().getAPWeight() < ts.getIntendedDestination().getAPWeight() and nextDest.getAPWeight() == 0):
                        tsStr = str(nextDest.getStateString())+str(ts.getIntendedDestination().getStateString())+"_AD"

                        newTS = CoherenceState(tsStr, False)
                        newTS.setSource(nextDest)
                        newTS.setIntendedDestination(ts.getIntendedDestination())
                        newTS.setParent(ts)
                        newTS.setPreOrderedFlag()
                        newTS.copyStateEncoding(nextDest)

                        tstate = self.addPreOrderedState(newTS)

                        t = Transition(ts, e, tstate)
                        self.addTransition(t)

                    elif (ts.getSource().getAPWeight() > ts.getIntendedDestination().getAPWeight()):
                        # MS_A, MI_A, OI_A, EI_A, ES_A
                        if (ts.getSource().getPCPWeight() == 1 and (nextDest.getAPWeight() == 0 or ts.getIntendedDestination().getAPWeight() == 0)):
                            if (configModel == "direct"):
                                invStableState = self.getInvalidStableState()
                                # next dest is I, create II_A
                                tsStr = str(invStableState.getStateString())+str(invStableState.getStateString())+"_A"

                                newTS = CoherenceState(tsStr, False)
                                newTS.setSource(ts)
                                newTS.setIntendedDestination(invStableState)
                                newTS.setParent(ts)
                                newTS.setPreOrderedFlag()
                                newTS.copyStateEncoding(invStableState)

                                tstate = self.addPreOrderedState(newTS)

                                t1 = Transition(ts, e, tstate)
                                t1.setAction("Send data")
                                t2 = Transition(tstate, "Ordered", invStableState)

                                self.addTransition(t1)
                                self.addTransition(t2)
                            else:
                                if (ts.getIntendedDestination().getAPWeight() != nextDest.getAPWeight()):
                                    tsStr = str(ts.getSource().getStateString())+str(nextDest.getStateString())+"_A"
                                    newTS = CoherenceState(tsStr, False)
                                    newTS.setSource(ts)
                                    newTS.setIntendedDestination(nextDest)
                                    newTS.setParent(ts)
                                    newTS.setPreOrderedFlag()
                                    newTS.copyStateEncoding(ts.getSource())

                                    tstate = self.addPreOrderedState(newTS)

                                    t1 = Transition(ts, e, tstate)
                                    t2 = Transition(tstate, "Ordered", nextDest)
                                    
                                    if (ts.getSource().getSMPWeight() > 0):
                                        t2.setAction("Write-back data")
                                    else:
                                        t2.setAction("Communicate message")

                                    self.addTransition(t1)
                                    self.addTransition(t2)
                                else:
                                    t = Transition(ts, e, ts)
                                    self.addTransition(t)
                        else:
                            t = Transition(ts, e, ts)
                            self.addTransition(t)
                    elif (ts.getSource().getPCPWeight() > nextDest.getPCPWeight()):
                        tsStr = str(nextDest.getStateString())+str(ts.getIntendedDestination().getStateString())+"_AD"
                        newTS = CoherenceState(tsStr, False)
                        newTS.setSource(ts)
                        newTS.setIntendedDestination(ts.getIntendedDestination())
                        newTS.setParent(ts)
                        newTS.setPreOrderedFlag()
                        newTS.copyStateEncoding(nextDest)

                        t = Transition(ts, e, newTS)
                        t.setAction("Send data")
                        self.addTransition(t)
                
    def postOrderedTransitions(self, configModel): 
        O = ["OtherRead", "OtherWrite"]
        for ts in self.postOrderedStates:
            for e in O:
                nextDest = self.getTransitionDestination(ts.getIntendedDestination(), e)
                # TODO: need to change this to something more comprehensive
                if (nextDest.getAPWeight() == ts.getIntendedDestination().getAPWeight()):
                    t = Transition(ts, e, ts)
                    self.addTransition(t)
                else:
                    tsStr1 = str(ts.getStateString())+str(nextDest.getStateString())+"_D"

                    newTS1 = CoherenceState(tsStr1, False)
                    newTS1.setSource(ts)
                    newTS1.setIntendedDestination(nextDest)
                    newTS1.setParent(ts)
                    newTS1.copyStateEncoding(nextDest)

                    tstate1 = self.addPostOrderedState(newTS1);

                    t1 = Transition(ts, e, tstate1)
                    self.addTransition(t1)

                    parent = None
                    nxt = ts
                    while(nxt.getParent() != None):
                        parent = nxt.getParent()
                        nxt = parent
                        
                    # Check if a transition needs transient state or not..
                    tmpT = Transition(ts.getIntendedDestination(), e, nextDest)
                    needTransientState = self.asymptoticLatencyAnalysisTransition(tmpT, configModel)
                    if (needTransientState): 
                        tsStr2 = str(parent.getIntendedDestination().getStateString())+str(nextDest.getStateString())+"_A"

                        newTS2 = CoherenceState(tsStr2, False)
                        newTS2.setSource(newTS1)
                        newTS2.setIntendedDestination(nextDest)
                        newTS2.setParent(ts)
                        newTS2.setPreOrderedFlag()
                        newTS1.copyStateEncoding(newTS1)

                        tstate2 = self.addPreOrderedState(newTS2)

                        t1 = Transition(newTS1, "Data", tstate2)
                        self.addTransition(t1)
                    else:
                        t1 = Transition(tstate1, "Data", nextDest)
                        self.addTransition(t1)

    def constructMemStateMachine(self, configModel):
        # at least two states: invalid, and modified
        newIState = CoherenceState('SM_I', True)
        newMState = CoherenceState('SM_M', True)
        newXState = CoherenceState('SM_X', True)
        newFState = CoherenceState('SM_F', True)

        newIState.setAP("invalid")
        newIState.setSMP("clean")
        newMState.setAP("write")
        newMState.setSMP("dirty")
        newMState.setPCP("active")
        
        self.addMemState(newIState)
        self.addMemState(newMState)

        # when to add new states
        if (self.isExclusiveStateExists()):
            newXState.setAP("read")
            newXState.setSMP("clean")
            newXState.setPCP("passive")
            #if (self.isExclusiveDirtyStateExists()):
            #    newXState.setSMP("dirty")
            #else:
            #    newXState.setSMP("clean")
            self.addMemState(newXState) 
        if (self.isForwardingStateExists()):
            newFState.setAP("read")
            newFState.setSMP("clean")
            newFState.setPCP("active")
            self.addMemState(newFState)

        # now the sauce..., make transitions
        if (configModel == "memory"):
            # all communication is through the shared memory
            for s in self.memStates:
                for e in ['GetS', 'GetM', 'PutM']:
                    if (s.isTransientState() == True):
                        # simply stall until we reach a stable state
                        t = Transition(s, str(e)+"/Stall", s)
                        self.addMemTransition(t)
                    else:
                        if (s.getAPWeight() < 1):
                            # read access
                            if (e == 'GetS'):
                                if (self.isExclusiveStateExists()):
                                    t = Transition(s, str(e), newMState)
                                    t.setAction("Set owner, Send data")
                                    self.addMemTransition(t)
                                else:
                                    t = Transition(s, str(e), s)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                            if (e == 'GetM'):
                                t = Transition(s, str(e), newMState)
                                t.setAction("Set owner, Send data")
                                self.addMemTransition(t)
                            #if (e == 'PutM'): cannot happen for this

                        else:
                            if (s.getSMPWeight() > 0):
                                # write access with dirty
                                newTStateStr = s.getStateString() + "_D"
                                newTState = CoherenceState(newTStateStr, False)
                                self.addMemState(newTState)
                                t1 = Transition(s, e, newTState)
                                if (e == "PutM"):
                                    t2 = Transition(newTState, "Ordered", newIState)
                                    t2.setAction("Write-back data")
                                    self.addMemTransition(t1)
                                    self.addMemTransition(t2)
                                else:
                                    if (self.isExclusiveStateExists()):
                                        t2 = Transition(newTState, "Receive data", newXState)
                                        self.addMemTransition(t1)
                                        self.addMemTransition(t2)
                                    else:
                                        t2 = Transition(newTState, "Receive data", newIState)
                                        self.addMemTransition(t1)
                                        self.addMemTransition(t2)
                            else:
                                # read access with clean
                                if (e == 'GetS'):
                                    t = Transition(s, str(e), s)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                                if (e == 'GetM'):
                                    t = Transition(s, str(e), newMState)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                                #if (e == 'PutM'): cannot happen
        else:
            # communication through SM/cache-to-cache
            for s in self.memStates:
                for e in ['GetS', 'GetM', 'PutM']:
                    if (s.isTransientState() == True):
                        if (e == 'GetS'):
                            t = Transition(s, str(e), s)
                            t.setAction("Stall")
                            self.addMemTransition(t)
                        if (e == 'GetM'):
                            t = Transition(s, str(e), newMState)
                            self.addMemTransition(t)
                    else:
                        if (s.getAPWeight() < 1):
                            # invalid access
                            if (e == 'GetS'):
                                if (self.isExclusiveStateExists()):
                                    t = Transition(s, str(e), newMState)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                                elif (self.isForwardingStateExists()):
                                    t = Transition(s, str(e), newFState)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                                else:
                                    t = Transition(s, str(e), s)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                            if (e == 'GetM'):
                                t = Transition(s, str(e), newMState)
                                t.setAction("Send data")
                                self.addMemTransition(t)
                        else:
                            if (s.getSMPWeight() > 0):
                                # write access with dirty
                                newTStateStr = s.getStateString() + "_D"
                                newTState = CoherenceState(newTStateStr, False)

                                if (e == 'GetM'):
                                    t = Transition(s, e, newMState)
                                    self.addMemTransition(t)
                                if (e == 'PutM'):
                                    t1 = Transition(s, e, newTState)
                                    t2 = Transition(newTState, "Ordered", newIState)
                                    t2.setAction("Write-back data")
                                    self.addMemState(newTState)
                                    self.addMemTransition(t1)
                                    self.addMemTransition(t2)

                                else:
                                    self.addMemState(newTState)
                                    t1 = Transition(s, e, newTState)
                                    if (self.isForwardingStateExists()):
                                        t2 = Transition(newTState, "Receive data", newFState)
                                        self.addMemTransition(t1)
                                        self.addMemTransition(t2)
                                    elif (self.isExclusiveStateExists()):
                                        t2 = Transition(newTState, "Receive data", newXState)
                                        self.addMemTransition(t1)
                                        self.addMemTransition(t2)
                                    else:
                                        t2 = Transition(newTState, "Receive data", newIState)
                                        self.addMemTransition(t1)
                                        self.addMemTransition(t2)
                            elif (s.getPCPWeight() < 1):
                                if (e == 'GetS'):
                                    if (self.isForwardingStateExists()):
                                        t = Transition(s, str(e), newFState)
                                        t.setAction("Set owner, send data")
                                        self.addMemTransition(t)
                                    else:
                                        t = Transition(s, str(e), s)
                                        t.setAction("Send data")
                                        self.addMemTransition(t)
                                if (e == 'GetM'):
                                    t = Transition(s, str(e), newMState)
                                    t.setAction("Send data")
                                    self.addMemTransition(t)
                            else:
                                if (e == 'GetS'):
                                    t = Transition(s, str(e), s)
                                    t.setAction("Set owner")
                                    self.addMemTransition(t)
                                if (e == 'GetM'):
                                    t = Transition(s, str(e), newMState)
                                    t.setAction("Set owner, send data")
                                    self.addMemTransition(t)
                                if (e == 'PutM'):
                                    newTStateStr = s.getStateString() + "_A"
                                    newTState = CoherenceState(newTStateStr, False)
                                    self.addMemState(newTState)
                                    t1 = Transition(s, e, newTState)
                                    self.addMemTransition(t1)
                                    if (self.isExclusiveStateExists()):
                                        t2 = Transition(newTState, "Ordered", newXState)
                                        self.addMemTransition(t2)
                                    else:
                                        t2 = Transition(newTState, "Ordered", newIState)
                                        self.addMemTransition(t2)

    def asymptoticLatencyAnalysisTransition(self, t, configModel):
        sv = ()
        tv = ()
        ev = ()

        EV = []

        states = []

        if (t.getTriggerEvent() == "OtherRead"):
            if (t.getSource().getPCPWeight() > 0):
                EV = [("OwnReadP", "OtherRead")]
                states = [self.getInvalidStableState()]
            else:
                EV = [("OwnReadM", "OtherRead"), ("OwnReadP", "OtherRead")]
                states = self.states
            for ev in EV:
                for s in states:
                    if s.isTransientState():
                        sv = StateView(s.getSource(), t.getStableSource())
                    else:
                        sv = StateView(s, t.getStableSource())

                    if (sv.isValid()):
                        d1 = self.getTransitionDestination(sv.getState(0), ev[0])
                        d2 = self.getTransitionDestination(sv.getState(1), ev[1])
                        tv = StateView(d1, d2)

                        # need to check if there are bcasts
                        if (d1 == sv.getState(0) or d2 == sv.getState(1)):
                            continue

                        cua = 0
                        if (ev[1] == "OwnWriteM" or ev[1] == "OwnReadM" or ev[1] == "OwnWriteP" or ev[1] == "OwnReadP"):
                            cua = 1


                        if (configModel == "memory"):
                            if (cua == 1):
                                if (d1.getSMPWeight() - sv.getState(1).getSMPWeight() < 0 or d1.getPCPWeight() - sv.getState(0).getPCPWeight() < 0):
                                    return True
                            else:
                                if (d2.getSMPWeight() - sv.getState(1).getSMPWeight() < 0 or d2.getPCPWeight() - sv.getState(1).getPCPWeight() < 0):
                                    return True
                        else: 
                            mvalDelta = tv.computeSMWeight() - sv.computeSMWeight()
                            pvalDelta = tv.computePPWeight() - sv.computePPWeight()

                        
                            if (mvalDelta < 0 and tv.getState(cua).getSMP() == sv.getState(cua).getSMP()):
                                return True


                            if (pvalDelta < 0 and tv.getState(cua).getPCP() == sv.getState(cua).getPCP()):
                                return True

        if (t.getTriggerEvent() == "OtherWrite"):
            if (t.getSource().getPCPWeight() > 0):
                EV = [("OwnWriteP", "OtherWrite")]
            else:
                EV = [("OwnWriteM", "OtherWrite"), ("OwnWriteP", "OtherWrite")]

            for ev in EV:
                for s in self.states:
                    if s.isTransientState():
                        sv = StateView(s.getSource(), t.getSource())
                    else:
                        sv = StateView(s, t.getSource())

                    
                    if (sv.isValid()):
                        d1 = self.getTransitionDestination(sv.getState(0), ev[0])
                        d2 = self.getTransitionDestination(sv.getState(1), ev[1])

                        tv = StateView(d1, d2)

                        cua = 0
                        if (ev[1] == "OwnWriteM" or ev[1] == "OwnReadM" or ev[1] == "OwnWriteP" or ev[1] == "OwnReadP"):
                            cua = 1


                        if (configModel == "memory"):
                            if (cua == 1):
                                if (d1.getSMPWeight() - sv.getState(0).getSMPWeight() < 0 or d1.getPCPWeight() - sv.getState(0).getPCPWeight() < 0):
                                    return True
                            else:
                                if (d2.getSMPWeight() - sv.getState(1).getSMPWeight() < 0 or d2.getPCPWeight() - sv.getState(1).getPCPWeight() < 0):
                                    return True
                        else: 
                            mvalDelta = tv.computeSMWeight() - sv.computeSMWeight()
                            pvalDelta = tv.computePPWeight() - sv.computePPWeight()


                            if (mvalDelta < 0 and tv.getState(cua).getSMP() == sv.getState(cua).getSMP()):
                                return True


                            if (pvalDelta < 0 and tv.getState(cua).getPCP() == sv.getState(cua).getPCP()):
                                return True
 
        return False
    
    def asymptoticLatencyAnalysis(self, configModel):
        for t in self.ipTransitions:
            if (self.asymptoticLatencyAnalysisTransition(t, configModel)):
                self.addNonLinearTransitions(t)
            else:
                self.addLinearTransitions(t)

    def completeAndVisualizeProtocol(self):
        stallTxn = 0
        for s in self.states:
            if (s.isTransientState() == True):
                for ev in ["OtherRead", "OtherWrite"]:
                    txnFound = False
                    for t in self.transitions:
                        if (t.getSource().state == s.getStateString() and t.getTriggerEvent() == ev):
                            txnFound = True
                            break

                    if (txnFound == False):
                        # transition with s and ev not found, create a stalling transition
                        t = Transition(s, "Stall", s)
                        self.transitions.append(t)
                        stallTxn = stallTxn+1
                
        print ("Total transitions: "+str(len(self.transitions)))
        print ("Total stall transitions: "+str(stallTxn))
        self.visualizeProtocol()

    def constructNonStallingProtocol(self, outputfile, configModel):

        #@@@@@@@@@@@@#
        # Step 1: Bus communication
        p1 = self.constructAtomicOwnImplementation()
        self.constructAtomicOtherImplementation(configModel)

        #print ("@@@@@ BUS COMMUNICATION @@@@@@@")
        #tmpProtocol = CoherenceProtocol()
        #tmpProtocol.states = copy.deepcopy(self.states)
        #tmpProtocol.transitions = copy.deepcopy(self.transitions)
        #tmpProtocol.completeAndVisualizeProtocol()

        #@@@@@@@@@@@@#
        # step 2: Interleaving
        # step 2.1: pre-ordered
        self.preOrderedTransitions(configModel)

        #print ("@@@@@@@@@@@@@@")
        #print ("@@@@@ PRE-ORDERED @@@@@@@")
        #tmpProtocol.states = copy.deepcopy(self.states)
        #tmpProtocol.transitions = copy.deepcopy(self.transitions)
        #tmpProtocol.completeAndVisualizeProtocol()

        # step 2.2: post-ordered
        self.postOrderedTransitions(configModel)

        #print ("@@@@@@@@@@@@@@")
        #print ("@@@@@ POST-ORDERED @@@@@@@")
        #tmpProtocol.states = copy.deepcopy(self.states)
        #tmpProtocol.transitions = copy.deepcopy(self.transitions)
        #tmpProtocol.completeAndVisualizeProtocol()

        #@@@@@@@@@@@@#
        # step 4: replacement
        self.handleReplacements()

        #@@@@@@@@@@@@#
        # step 4: run preOrdered again
        # steps 3 and 4 may have introduced new pre-ordered transient states
        self.preOrderedTransitions(configModel)

        #@@@@@@@@@@@@#
        # step 5: create memory state machine
        self.constructMemStateMachine(configModel)

        self.visualizeProtocol()

    def handleReplacements(self):
        invStableState = self.getInvalidStableState()
        for s in self.states:
            if (s.isTransientState() == False):
                # check if state has active data authority
                if (s.getPCPWeight() > 0):
                    tsStr = str(s.getStateString()) + str(invStableState.getStateString())+"_A"

                    ts = CoherenceState(tsStr, False)
                    ts.setSource(s)
                    ts.setIntendedDestination(invStableState)
                    ts.setPreOrderedFlag()
                    ts.copyStateEncoding(s)

                    tstate = self.addPreOrderedState(ts)

                    t1 = Transition(s, "Replacement", tstate)
                    t2 = Transition(tstate, "Ordered", invStableState)
                    self.addTransition(t1)
                    self.addTransition(t2)
                elif (s.getSMPWeight() > 0):
                    tsStr = str(s.getStateString()) + str(invStableState.getStateString())+"_A"

                    ts = CoherenceState(tsStr, False)
                    ts.setSource(s)
                    ts.setIntendedDestination(invStableState)
                    ts.setPreOrderedFlag()
                    ts.copyStateEncoding(s)

                    tstate = self.addPreOrderedState(ts)

                    t1 = Transition(s, "Replacement", tstate)
                    t2 = Transition(tstate, "Ordered, Write-back data", invStableState)
                    self.addTransition(t1)
                    self.addTransition(t2)

                elif (s.getAPWeight() > 0):
                    t = Transition(s, "Replacement", invStableState)
                    self.addTransition(t)


    def getInvalidStableState(self):
        for s in self.states:
            if (s.isTransientState() == False and s.getAPWeight() == 0):
                return s
        assert True

    def constructAtomicOwnImplementation(self):
        O = ["OwnWriteM", "OwnWriteP", "OwnReadM", "OwnReadP"]

        transitions = self.transitions.copy() 
        for t in transitions:
            if (t.getTriggerEvent() in O):
                if (t.getSource().getAPWeight() < 2 and t.getSource().getAPWeight() != t.getDestination().getAPWeight()):
                    tsStr1 = str(t.getSource().getStateString())+str(t.getDestination().getStateString())+"_AD" 
                    tsStr2 = str(t.getSource().getStateString())+str(t.getDestination().getStateString())+"_D" 
                    #ts1 = TransientState(tsStr1, t.getSource(), t.getDestination(), None)
                    #ts2 = TransientState(tsStr2, t.getSource(), t.getDestination(), ts1)

                    ts1 = CoherenceState(tsStr1, False)
                    ts1.setSource(t.getSource())
                    ts1.setIntendedDestination(t.getDestination())
                    ts1.setPreOrderedFlag()
                    ts1.copyStateEncoding(t.getSource())
                    tstate1 = self.addPreOrderedState(ts1)

                    ts2 = CoherenceState(tsStr2, False)
                    ts2.setSource(t.getSource())
                    ts2.setIntendedDestination(t.getDestination())
                    ts2.setParent(ts1)
                    ts2.copyStateEncoding(t.getDestination())
                    tstate2 = self.addPostOrderedState(ts2)

                    t1 = Transition(t.getSource(), t.getTriggerEvent(), tstate1)
                    t2 = Transition(tstate1, "Ordered", tstate2)
                    t3 = Transition(tstate2, "Data", t.getDestination())

                    self.transitions.remove(t)
                    self.addTransition(t1)
                    self.addTransition(t2)
                    self.addTransition(t3)

                # To support upgrades 
                #elif (t.getDestination().getAPWeight() > t.getSource().getAPWeight()):
                #    tsStr = str(t.getSource().getStateString())+str(t.getDestination().getStateString())+"_A"
                #    ts = CoherenceState(tsStr, False)
                #    ts.setSource(t.getSource())
                #    ts.setIntendedDestination(t.getDestination())
                #    ts.setPreOrderedFlag()
                #    ts.copyStateEncoding(t.getSource())
                #    tstate = self.addPreOrderedState(ts)

                #    t1 = Transition(t.getSource(), t.getTriggerEvent(), tstate)
                #    t2 = Transition(tstate, "Ordered", t.getDestination())
                #    self.transitions.remove(t)
                #    self.addTransition(t1)
                #    self.addTransition(t2)

    def constructAtomicOtherImplementation(self, configModel):
        O = ["OtherRead", "OtherWrite"]
        transitions = self.transitions.copy()
        for t in transitions:
            if (t.getTriggerEvent() in O):
                if (t.getSource().getStateString() != t.getDestination().getStateString() and t.getSource().getAPWeight() > 0):
                    addNewTS = self.asymptoticLatencyAnalysisTransition(t, configModel)
                    if (addNewTS):
                        tsStr = str(t.getSource().getStateString()) + str(t.getDestination().getStateString()) +  "_A"
                        #ts = TransientState(tsStr, t.getSource(), t.getDestination(), None)

                        ts = CoherenceState(tsStr, False)
                        ts.setSource(t.getSource())
                        ts.setIntendedDestination(t.getDestination())
                        ts.setPreOrderedFlag()
                        ts.copyStateEncoding(t.getSource()) 
                        tstate = self.addPreOrderedState(ts)

                        t1 = Transition(t.getSource(), t.getTriggerEvent(), tstate)
                        actionString = "Ordered"

                        if (t.getSource().getPCPWeight() > 0):
                            t2 = Transition(tstate, "Ordered", t.getDestination())
                            if (configModel == "direct"):
                                t2.setAction("Send data")
                            else:
                                t2.setAction(" Write-back data")

                        self.transitions.remove(t)
                        self.addTransition(t1)
                        self.addTransition(t2)

                    else:
                        if (t.getSource().getPCPWeight() > 0):
                            # must be direct config model
                            t.setAction("Send data")


def parse(inputFile, inputCoherenceProtocol):

    f = open(str(inputFile), "r")
    flines = f.readlines()

    parseState = 'idle'

    stateMap = {}

    for line in flines:
        stateDemarkSearch = re.search(r'@ State modeling', line, re.M|re.I)
        txnDemarkSearch = re.search(r'@ Txn specs', line, re.M|re.I)
        commentLine = re.match(r'^#.*', line, re.M|re.I)

        if (commentLine):
            continue
        if (stateDemarkSearch):
            parseState = 'state'
        elif (txnDemarkSearch):
            parseState = 'txn'
        else :
            if (parseState == 'state'):
                stateEncodeExp = re.match(r'(.*) -> \((.*), (.*), (.*)\)', line, re.M|re.I)

                if (stateEncodeExp):
                    state = str(stateEncodeExp.group(1))
                    ap = str(stateEncodeExp.group(2))
                    pc = str(stateEncodeExp.group(3))
                    sm = str(stateEncodeExp.group(4))

                    cohState = CoherenceState(state, True)
                    cohState.setAP(ap)
                    cohState.setSMP(sm)
                    cohState.setPCP(pc)

                    inputCoherenceProtocol.addState(cohState)
                    stateMap[state] = cohState
 
            elif (parseState == 'txn'):
                txnEncodeExp = re.match(r'\((.*), (.*)\) -> (.*)', line, re.M|re.I)

                if (txnEncodeExp):
                    source = txnEncodeExp.group(1)
                    destination = txnEncodeExp.group(3)
                    event = txnEncodeExp.group(2)

                    sourceState = stateMap[source]
                    destState = stateMap[destination]

                    transition = Transition(sourceState, event, destState)
                    inputCoherenceProtocol.addTransition(transition)

    parseState = 'idle'


def analyzeProtocol(inputFile, configModel):

    inputCoherenceProtocol = CoherenceProtocol()

    # parse and populate stateMap, txnMap
    parse(inputFile, inputCoherenceProtocol)
    
    # construct U_p
    inputCoherenceProtocol.constructU()

    # asymptotic latency analysis
    inputCoherenceProtocol.ipTransitions = inputCoherenceProtocol.transitions
    inputCoherenceProtocol.asymptoticLatencyAnalysis(configModel)

    if (inputCoherenceProtocol.isNonLinearLatency()):
        print ("Input protocol has non-linear WCAL bound")
        inputCoherenceProtocol.printNonLinearTransitions()
    else:
        print ("Input protocol has linear WCAL bound")

    return inputCoherenceProtocol

def main(argv):
    # main function
    inputfile= ' '
    outputfile= ' '
    configModel='direct' # memory: all communication through shared memory, direct: pt-to-pt communication

    try:
        opts, args = getopt.getopt(argv, "hi:s:", ["ifile=", "system-model="])
    except getopt.GetoptError:
        print ('synth.py -i <input-protocol> -s <system-model>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h' :
            print ('synth.py -i <input> -s <system-model>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
            outputfile = "linear-"+arg
        elif opt in ("-s", "--system-model"):
            configModel = arg

    print("@@@@@ Predictable protocol analyzer @@@@@")
    print(" ----- Step 1: Analyze protocol -----")
    ipCoherenceProtocol = analyzeProtocol(inputfile, configModel)
    ipCoherenceProtocol.ipStates = copy.deepcopy(ipCoherenceProtocol.states)
    ipCoherenceProtocol.ipTransitions = copy.deepcopy(ipCoherenceProtocol.transitions)

    print(" ----- Step 2: Non-stalling protocol implementation ----")
    ipCoherenceProtocol.constructNonStallingProtocol(inputfile, configModel)

if __name__ == "__main__":
    main(sys.argv[1:])
