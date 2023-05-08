from base64 import encode
from cmath import inf
from enum import Flag
import time
import copy
import itertools
from xmlrpc.client import boolean
import collections
import random as rand
import numpy as np
np.random.seed(0)


class marlEnvironment:
    
    def __init__(self, uncertainty, ammountOfCarriers, askAgain = True, ammountOfProducts=[50], breakdowns=1):
        self.uncertainty = uncertainty
        self.ammountOfCarriers = ammountOfCarriers
        self.askAgain = askAgain
        self.epiCnt = 0
        self.ammountOfProducts = ammountOfProducts
        self.breakdowns = breakdowns
        
        
    
    def getOperationTimesWithUncertainty(self, opTimes):
        temp = []
        for x in opTimes:
            temp.append(rand.randint(x-self.uncertainty, x+self.uncertainty))
        return temp
    

    def generateExponentialDistributedTimes(self, anzahl, rate):
        # Rate = 1 -> moderate
        # Rate = 2 -> high

        events = []
        for x in range(anzahl):

            TimeOfEntry = int((np.random.exponential(scale=1) *1000)/rate)
            if TimeOfEntry < (100/rate):
                TimeOfEntry = (100/rate)
            if TimeOfEntry >= (1800/rate):
                TimeOfEntry = (1800/rate)   


            Duration = int((np.random.exponential(scale=1) *60))
            if Duration < 15:
                Duration = 15

            events.append([
                    TimeOfEntry,
                    Duration
                    ])      
        
        return events
    
    def setUpEnv(self):
              
        self.order = []
        self.AllOperationsOrder = [1,2,3,4,5,6,7]
        self.productvariants = [
            # [A,B,C,D,E,F,G]
              [1,2,3,4,5,6,7],  
              [  2,3,  5,  7],
              [1,  3,4,  6  ],
              [  2,3,4,5,6  ]
        ]

          

        if len(self.ammountOfProducts) == 1:
            productsToBeManufactured = self.ammountOfProducts[0]
        else:
            productsToBeManufactured = rand.randint(self.ammountOfProducts[0], self.ammountOfProducts[1])
        
        for x in range(productsToBeManufactured):
            ProductVariant = rand.choice(self.productvariants) # 9 = ProductVariant
            self.order.append(
                [
                    ProductVariant,        # 0 = Work plan of the product
                    False,                  # 1 = Assignment of the carrier on which the product is manufactured (key)
                    False,                  # 2 = True, if the job has already been started/assigned
                    False,                  # 3 = True, if the order was finished
                    False,                  # 4 = Did an error occur during the p
                ]
            )
         

        self.log_probs = []
        self.values = []
        self.rewards = []

        self.stepCnt = 0

        self.amountOfOperations = 7

        self.operationsTimes = [
            self.getOperationTimesWithUncertainty([10,22,19]),            # Station #0        Operation: A,D,E    (10,40,50)      OpTimes:    (10,22,19)
            self.getOperationTimesWithUncertainty([15,18,24]),            # Station #1        Operation: b,D,E    (20,40,50)      OpTimes:    (15,18,24)
            self.getOperationTimesWithUncertainty([15,19,19]),            # Station #2        Operation: B,C,F    (20,30,60)      OpTimes:    (15,19,19)
            self.getOperationTimesWithUncertainty([16,17,10]),            # Station #3        Operation: C,F,G    (30,60,70)      OpTimes:    (16,17,10)
        ]

        self.stations = [
            [    #-----------------------------------------------------------
                                        # Station #1 (key=0)
                [1,4,5],                # 0 = Operation: 10,40,50
                self.operationsTimes[0],# 1 = OpTimes
                1,                      # 2 = PosOnConveyor
                [[],[1],[1]],           # 3 = StationNeighbours (keys)
                False,                  # 4 = Breakdowns
                "inIdle",               # 5 = State - inIdle, inProduction 
                [False, False, False],  # 6 = Breakdown States
            ], [ #-----------------------------------------------------------
                                        # Station #2 (key=1)
                [2,4,5],                # Operation: 20,40,50
                self.operationsTimes[1],# OpTimes
                7,                      # PosOnConveyor
                [[2],[0],[0]],          # 3 = StationNeighbours
                False,                  # 4 = Breakdowns
                "inIdle",               # 5 = State - inIdle, inProduction
                [False, False, False],  # 6 = Breakdown States
            ], [ #-----------------------------------------------------------
                                        # Station #3 (key=2)
                [2,3,6],                # Operation: 20, 30, 60
                self.operationsTimes[2],      # OpTimes
                13,                     # PosOnConveyor
                [[1],[3],[3]],          # 3 = StationNeighbours
                False,                  # 4 = Breakdowns
                "inIdle",               # 5 = State - inIdle, inProduction
                [False, False, False],  # 6 = Breakdown States
            ], [ #-----------------------------------------------------------
                                        # Station #4 (key=3)
                [3,6,7],                # Operation: 30,60,70
                self.operationsTimes[3],      # OpTimes
                19,                     # PosOnConveyor
                [[2],[2],[]],           # 3 = StationNeighbours
                False,                  # 4 = Breakdowns
                "inIdle",               # 5 = State - inIdle, inProduction
                [False, False, False],  # 6 = Breakdown States
            ]
        ]
            
        ################################################################################################
        # Breakdowns 
        for k, s in enumerate(self.stations):            
            aBreakdowns = []
            i = 0
            for o in s[0]:
                accumulatedOpTimes = 0
                aBreakdowns.append([])
                if o in [2,3,4,5,6]:
                    for x in self.generateExponentialDistributedTimes(productsToBeManufactured,self.breakdowns):
                                        
                        accumulatedOpTimes += x[0]            
                        aBreakdowns[i].append([
                            accumulatedOpTimes,     # 0 = Start         
                            x[1],                   # 1 = Duration        
                            False,                  # 2 = Real start
                            False                   # 3 = Real end
                        ])
                        accumulatedOpTimes += x[1]  
                else:
                    pass
                i += 1
            self.stations[k][4] = aBreakdowns
        ################################################################################################
        
        self.carrier = []
        self.carrierHistory = []            
        # F = Finished      
        # W = Waiting for Carrier before
        # T = Transport
        # B = Waiting for fixing Breakdowns


        # Decisionen für die Produkte initialiseren
        for x in range(self.ammountOfCarriers):

            self.carrier.append(
                [           # Carrier #XX
                            False,                              # 0 = nextOp
                            0,                                  # 1 = actPos 
                            0,                                  # 2 = OpProgress
                            0,                                  # 3 = stepCnt-ActionVonStation
                            (x+1),                              # 4 = CarrierID
                            0,                                  # 5 = CarrierShouldContinueMoving
                            0,                                  # 6 = stepCnt-ActionFromConveyor
                            False,                              # 7 = Decision: stationKey 
                            False,                              # 8 = Decision: skip    
                            False,                              # 9 = ProductVariant              
                            False,                              # 10= orderPos
                            False,                              # 11= Last operation for which was decided (nextOp)
                            False,                              # 12= Changed mind again                         
                ]
            )
            self.carrierHistory.append(
                [           # Carrier #XX
                            [],                 # 0 = HistoryStation        # key
                            [],                 # 1 = Time
                            [],                 # 2 = HistoryOperation      # nextOp
                ]
            )
    
        
        self.iLastCheckBreakdowns           = -1
        self.iLastCheckDecisionsNeeded      = -1
        self.iLastCheckOrderAssignment      = -1
        self.popedStationKey                = -1
        self.popedWorkplanKey               = -1
        self.popedCarrierKey                = -1
        self.popedOrderKey                  = -1
        self.popedOpKey                     = -1
        self.availableSkipTokens            = 10
        self.DecidedForFailureCnt           = 0
        self.epiTempReward                  = 0
        self.umentschiedenCnt               = 0
 

        self.orderDecisions = []
        for o in self.order:
            self.orderDecisions.append([])

        self.conveyor = [
            # Here are which carrierIds are in the slots....
            False,  # Pos =  1          Station 1
            False,  # Pos =  2
            False,  # Pos =  3
            False,  # Pos =  4
            False,  # Pos =  5
            False,  # Pos =  6
            False,  # Pos =  7          Station 2
            False,  # Pos =  8
            False,  # Pos =  9
            False,  # Pos =  10
            False,  # Pos =  11
            False,  # Pos =  12
            False,  # Pos =  13         Station 3
            False,  # Pos =  14
            False,  # Pos =  15
            False,  # Pos =  16
            False,  # Pos =  17
            False,  # Pos =  18
            False,  # Pos =  19         Station 4
            False,  # Pos =  20
            False,  # Pos =  21
            False,  # Pos =  22
            False,  # Pos =  23
            False,  # Pos =  24
        ]

        # Map the carrier randomly on the conveyor belt
        # First determine slots on the conveyor belt -> these receive the value "-1".
        for i in range(len(self.carrier)):
            foundFreeSlot = False
            while foundFreeSlot != True:
                slotID = rand.randint(1, len(self.conveyor))
                if self.conveyor[slotID-1] == False:
                    # Leeren Slot gefunden, Carrier zuweisen
                    self.conveyor[slotID-1] = -1
                    foundFreeSlot = True

        # Then replace all "-1" with CarrierID
        # This ensures that the carriers are in an orderly sequence
        for i in range(len(self.carrier)): 
            oneAdded = False
            for slotKey, slot in reversed(list((enumerate(self.conveyor)))): 
                if self.conveyor[slotKey] == -1 and oneAdded == False:
                    self.conveyor[slotKey] = i+1
                    self.carrier[i][1] = slotKey+1
                    oneAdded = True
        
        
        self.conveyorOrg = copy.deepcopy(self.conveyor) 
        self.carrierOrg = copy.deepcopy(self.carrier)
        self.stationsOrg = copy.deepcopy(self.stations)
        self.orderOrg = copy.deepcopy(self.order)


    def exportStartingConfiguration(self):
        return [
            self.conveyorOrg,
            self.carrierOrg,
            self.stationsOrg,
            self.orderOrg
        ]


    def productionFinished(self):
        retval = True
        
        for o in self.order:
            if o[3] == False:               # 3 = True, if the order was finished
                # at least one order has not been finished yet, so keep producing
                retval = False
                return retval
        
        return retval
                


    def getCarrierAtStation(self, keyForStation):
        # Return CarKey
        
        carAtS = False # carKey, oder False  
        for k, carIdOnConveyor in (enumerate(self.conveyor)): 
            if carIdOnConveyor != False: 

                slotID = k + 1
                carKey = carIdOnConveyor-1

                for stationKey, station in enumerate(self.stations): 
                    if (int(slotID) == int(station[2])):    
                        if stationKey == keyForStation:
                            carAtS = carKey
        return carAtS

    def isOperationRedundant(self, nextOp):
        retVal = False
        opCount = 0

        for k, station in (enumerate(self.stations)): 
            if nextOp in station[0]:
                opCount += 1
        
        if opCount >1:
            retVal = True
        
        return retVal

    def checkBreakdowns(self):
        for k, station in (enumerate(self.stations)): 
            if self.stations[k][5] == "inIdle":
                # The station is in the state "inIdle" -> is there now a fault?
                # does not work if the station is in the "inProduction" state
                
                # #######################################
                # Case 1 ###  Brackdown setzten
                # #######################################
                for opBKey, opBreakdown in enumerate(self.stations[k][4]):                    
                    for bKey, breakdown in enumerate(self.stations[k][4][opBKey]):
                        if breakdown[2] == False:
                            if self.stepCnt >= breakdown[0]:
                                self.stations[k][6][opBKey] = True
                                self.stations[k][4][opBKey][bKey][2] = self.stepCnt
                            break 
                        else:
                            # Die Störung wurde bereits gestartet
                            pass
            # #######################################
            # Case 2 ###  Brackdown zurücksetzten
            # #######################################                
            for opBKey, opBreakdown in enumerate(self.stations[k][4]):  
                relevantBKey = -1  
                for bKey, breakdown in enumerate(self.stations[k][4][opBKey]):                    
                    if breakdown[2] != False and breakdown[3] == False:
                        relevantBKey = bKey
                    
                if relevantBKey == -1:
                    pass
                else:
                    if self.stepCnt >= (self.stations[k][4][opBKey][relevantBKey][2] + self.stations[k][4][opBKey][relevantBKey][1]):
                        self.stations[k][6][opBKey] = False
                        self.stations[k][4][opBKey][relevantBKey][3] = self.stepCnt
           
 


    def assigningOrdersToEmptyCarriers(self):
        for k, station in (enumerate(self.stations)): 
            carAtS = self.getCarrierAtStation(k) # get carKey at Station
            if str(carAtS) == "False":
                pass
            else:
                c = self.carrier[carAtS]
                if str(c[10]) == "False":                   
                    notAssignedOrders = self.getProductvariantsFromNotAssignedOrderForStation(k) # list of orderKeys
                    if len(notAssignedOrders) > 0:

                        orderKey = notAssignedOrders[0]

                        self.order[orderKey][1] = carAtS      
                        self.order[orderKey][2] = True    

                        self.carrier[carAtS][0] = self.order[orderKey][0][0] # 0 = nextOp 
                        self.carrier[carAtS][9] = self.order[orderKey][0]    # 9 = ProductVariant 
                        self.carrier[carAtS][10]= orderKey                   # 10= orderPos (OrderKey


    def checkIfADecisionForACarrierIsNeeded(self):

        ratvalStationIds = []
        ratvalWorkplanOnCarrier = []
        retvalCarriers = []
        retvalOps = []
        retvalOrder = []

        for stationKey, station in (enumerate(self.stations)): 
            carAtS = self.getCarrierAtStation(stationKey) # get carKey at Station
            if str(carAtS) == "False":
                pass
            else:
                c = self.carrier[carAtS]
                if str(c[10]) == "False":
                    pass
                else:
                    nextOp = self.carrier[carAtS][0]
                    if  self.carrier[carAtS][2] == 0:
                        
                        isRedundant = self.isOperationRedundant(nextOp)
                        if isRedundant:
                            if (str(self.carrier[carAtS][7]) == "False") and (str(self.carrier[carAtS][8]) == "False"):   

                                ratvalStationIds.append(stationKey)  
                                ratvalWorkplanOnCarrier.append(self.carrier[carAtS][9])   # Append Workplan like [1,2,3]       
                                retvalCarriers.append(carAtS)
                                retvalOps.append(nextOp)                                  # 0 = nextOp
                                retvalOrder.append(self.carrier[carAtS][10])              #10 = orderPos
                            else:
                                if self.isTheNextOperationAccessible(nextOp, self.carrier[carAtS][7]) == False:
                                    if self.isAlternativAccessible(nextOp, self.carrier[carAtS][7]):
                                        if self.askAgain:
                                            ratvalStationIds.append(stationKey)  
                                            ratvalWorkplanOnCarrier.append(self.carrier[carAtS][9])   # Append Workplan like [1,2,3]       
                                            retvalCarriers.append(carAtS)
                                            retvalOps.append(nextOp)                                  # 0 = nextOp
                                            retvalOrder.append(self.carrier[carAtS][10])              #10 = orderPos
                                            self.umentschiedenCnt += 1
                                

        return [ratvalStationIds,ratvalWorkplanOnCarrier, retvalCarriers, retvalOps, retvalOrder]                  


    def getFollowingOperation(self,actOp, ProductVariant):
        try:
            index = ProductVariant.index(actOp)
            length = len(ProductVariant)
            if index == -1:
                ValueError("Error#1")
            else:
                if length > index+1:
                    nextIndex = ProductVariant[index+1]
                    retVal = nextIndex
                else:
                    retVal = False
        except:
            retVal = False   

        return retVal

    def getNotAssignedOrderKeys(self):
        retval = []
        for k, o in enumerate(self.order):
            if o[2] == False:     
                retval.append(k)
        return retval

    def getFirstNotAssignedOrderKeyForProductvariant(self, pv):
        retval = False
        for k, o in enumerate(self.order):
            if o[0] == pv:
                if o[2] == False:     
                    return k
        return retval
    
    def getProductvariantsFromNotAssignedOrderForStation(self, stationKey):
        notAssignedOrderKeys = []

        for pv in self.productvariants:
            if pv[0] in self.stations[stationKey][0]:            
                orderKey = self.getFirstNotAssignedOrderKeyForProductvariant(pv)
                if str(orderKey) == "False":
                    pass
                else:
                    notAssignedOrderKeys.append(orderKey)
        
        return notAssignedOrderKeys

     
    def getIndividualWaitingstimes(self):
        iMin = inf
        iMax = -inf
        allWainting = []
        avgWait = 0

        for ch in self.carrierHistory:
            temp = 0
            for hist in ch[0]:
                if hist == "W":
                    temp += 1
            allWainting.append(temp)

        for w in allWainting:
            if w < iMin:
                iMin = w
            if w > iMax:
                iMax = w
        
        avgWait = np.mean(allWainting)
        return [iMin, avgWait, iMax, allWainting]

    def calcReward(self,duration, actions=[]):

        ############################################################
        ############################################################
        ### Reward
        ############################################################
        ############################################################

        overallWaiting = 0
        overallTransport = 0
        overallBreakdown = 0

        ############################################################
        # 1. Determine all waitOpTimese
        ############################################################
        for ch in self.carrierHistory:
            for hist in ch[0]:
                if hist == "W":
                    overallWaiting += 1
                elif hist == "T":
                    overallTransport += 1
                elif hist == "B":
                    overallBreakdown += 1


        lastWaiting = 0
        ############################################################
        # 2. Determine waitOpTimes of the last carrier
        ############################################################
        for hist in self.carrierHistory[-1][0]:
            if hist == "W":
                lastWaiting += 1

        ############################################################   
        # 3. Determine parallel opTimes
        ############################################################
        

        operations=[2,3,4,5,6]
        operationTimes = {}


        for o in operations:
            operationTimes.update({o: 0})


        for i in range(duration):
            temp=[]
            for ch in self.carrierHistory:
                temp.append(ch[2][i])

            for o in operations:
                c = temp.count(o)
                if c >= 2:
                    operationTimes.update({o: (operationTimes[o]+1)})


        overallparalelTimes = 0
        x = operationTimes.values()
        for pt in x:
            overallparalelTimes += pt

        ############################################################   
        # 4. Determine token consumption
        ############################################################
        tooManyTokensNeeded = 0
        if self.availableSkipTokens < 0:
            # If negative, then more skips were requested than allowed.
            # (the additional skips are not executed, but the AI should still be penalized)
            # To find out how many too many were needed, the number must become Posetiv again, therefore *(-1)
            tooManyTokensNeeded = -(self.availableSkipTokens)  

        ############################################################   
        # 10. Compose Reward
        ############################################################
        
        penalty = 0
        bonus   = 0
        

        bonus =     (  3.0* overallparalelTimes)
        penalty =   (  2.0* overallTransport)                   +\
                    (  5.0* duration)                           +\
                    (  5.0* overallWaiting)                     +\
                    ( 10.0* overallBreakdown)                   +\
                    (  0.0* self.DecidedForFailureCnt)   +\
                    (100.0* tooManyTokensNeeded)
        
        reward = bonus - penalty

        ############################################################   
        # 11. scal Reward
        ############################################################


        # Reward: Offeset 
        reward += 50*1000
   
        # clip Reward
        if reward <=0:
            reward = 0

        ############################################################   
        # 20. Cnt up epi
        ############################################################
        self.epiCnt +=1

        return [reward, overallWaiting, overallparalelTimes]

    def getActualState(self):

        # State=
        #       |----- here ----|
        #       |Conveyor|Faults|


        # 0000 0000 conveyor slot is empty
        # 1000 0000 conveyor slot has an carrier, but without an product
        # 1000 1111 conveyor slot has an carrier, and product need Op 40,50,60,70

        retval = []
        finishedOrder = 0
        
        #########################################################################
        # Conveyores

        for k, conv in enumerate(self.conveyor):
            if conv == False:
                # conveyor slot is empty
                retval.append(0)  # Car in Slot
 
                for x in self.AllOperationsOrder:
                    retval.append(int(0)) 
            else:

                retval.append(1)  # Car in Slot

                carID = conv
                carKey = carID-1

                nextOp  = self.carrier[carKey][0]   # nextOp
                pv      = self.carrier[carKey][9]   # ProductVariant
                if str(nextOp) == "False" or str(pv) == "False":
                    for x in self.AllOperationsOrder:
                        retval.append(int(0)) 
                else:
                       for i in self.AllOperationsOrder:
                        if i in pv:
                            if i >= nextOp:
                                retval.append(int(1)) 
                            else:
                                retval.append(int(0))            
                        else:
                            retval.append(int(0))
                     
        #########################################################################
        # Faults
        for s in self.stations:
            for BreakdownState in s[6]:
                retval.append(int(BreakdownState))

        retval = np.array(retval) #convert to np Array
        return retval
    
    def startATrainEpisode(self, conveyor=False, carrier=False, stations=False , order=False):
        self.setUpEnv()

        if conveyor != False or carrier != False or stations != False or order != False:
            self.conveyor = conveyor
            self.carrier = carrier
            self.stations = stations
            self.order = order
        
        return self.stepUntilNextDecision() #Finished, Reward, actualState, stationID (0, at end)

    def startAnEvalEpisode(self, conveyor, carrier, stations, order):
        self.setUpEnv()
        self.conveyor = conveyor
        self.carrier = carrier
        self.stations = stations
        self.order = order
        
        return self.stepUntilNextDecision() #Finished, Reward, actualState, stationID (0, at end)

    def step(self, action):
        self.popedStationKey    
        self.popedWorkplanKey   
        self.popedCarrierKey    
        self.epiTempReward = 0


        # Possible value range    
        # 0 == 00 = Do not skip; Use station with index = 0
        # 1 == 01 = Do not skip; Use station with index = 1
        # 2 == 10 = Please skip; Use station with index = 0
        # 3 == 11 = Please skip; Use station with index = 1
        
        #      XX
        #      ||__ 0,1= Index     
        #      |___ 1  = Skipping, if possible
    

        #Decision    False  True
        #Decision    0,2    1,3
        #Decision    00,10  01,11
        #OpA		    [0       ]          # Op1
        #OpB 		    [1,     2]          # Op2
        #OpC		    [2,     3]          # Op3
        #OpD		    [0,     1]          # Op4
        #OpE		    [0,     1]          # Op5
        #OpF		    [2,     3]          # Op6
        #OpG		    [3       ]          # op7
        
        if action == 0:
            skipping    = 0
            actionIndex = 0            
        if action == 1:
            skipping    = 0
            actionIndex = 1            
        if action == 2:
            skipping    = 1
            actionIndex = 0
        if action == 3:
            skipping    = 1
            actionIndex = 1

        
        nextOp = self.carrier[self.popedCarrierKey][0] 
        stationIndex = False

        if nextOp == 2:
            # OpB - Op2
            if actionIndex == 0:
                stationIndex = 1
            elif actionIndex == 1:
                stationIndex = 2
        elif nextOp == 3:
            # OpC - Op3
            if actionIndex == 0:
                stationIndex = 2
            elif actionIndex == 1:
                stationIndex = 3           
        elif nextOp == 4:
            # OpD - Op4
            if actionIndex == 0:
                stationIndex = 0
            elif actionIndex == 1:
                stationIndex = 1   
        elif nextOp == 5:
            # OpE - Op5
            if actionIndex == 0:
                stationIndex = 0
            elif actionIndex == 1:
                stationIndex = 1           
        elif nextOp == 6:
            # OpF - Op6
            if actionIndex == 0:
                stationIndex = 2
            elif actionIndex == 1:
                stationIndex = 3         
          

        self.carrier[self.popedCarrierKey][7]     = stationIndex                            # Decision: stationKey 
        self.carrier[self.popedCarrierKey][8]     = skipping                                # Decision: skipp     
        self.carrier[self.popedCarrierKey][11]    = self.carrier[self.popedCarrierKey][0]   # NextOp

        if self.isTheNextOperationAccessible(nextOp, stationIndex) == False:
            self.DecidedForFailureCnt += 1
            self.epiTempReward -=50000      # add extra penalty

        return self.stepUntilNextDecision() #Finished, Reward, actualState, station
        
    def isAlternativAccessible(self, nextOp, stationKey):
        retVal = False
        for sKey, s in enumerate(self.stations): 
            if stationKey == sKey:
                pass
            else:
                for opKey, op in enumerate(self.stations[sKey][0]): 
                    if nextOp == op:
                        retVal = self.isTheNextOperationAccessible(nextOp, sKey)
        return retVal

    def isTheNextOperationAccessible(self, nextOp, stationKey):
        retVal = False

        index = -1
        for opKey, op in enumerate(self.stations[stationKey][0]): 
            if nextOp == op:
                index = opKey
        
        if index == -1:
            ValueError("Error#2")
            retVal = False
        else:
            breakdown = self.stations[stationKey][6][index]

            if breakdown == True:
                retVal = False
            else: 
                retVal = True

        return retVal


    def shouldTheNextOperationExecuted(self, nextOp, stationKey, carKey):
        ausfuehren = False
        carrierRelease = False


        isRedundant = self.isOperationRedundant(nextOp)

        if isRedundant == False:
            ausfuehren = True        
        else:         
            executeIndex = self.carrier[carKey][7]     
            skipping     = self.carrier[carKey][8]     

            if stationKey == executeIndex:                              
                accessible = self.isTheNextOperationAccessible(nextOp, stationKey)

                if accessible:

                    if skipping == 1:
                        self.availableSkipTokens -=1 

                        if self.availableSkipTokens >= 0:
                            self.carrier[carKey][8] = 0
                            ausfuehren = False
                            carrierRelease = True
                        else:
                            ausfuehren = True
                    else: 
                        ausfuehren = True
                
                
                else:
                    ausfuehren = False
                    carrierRelease = False
                    
            
            else:
                ausfuehren = False
                carrierRelease = True

        return [ausfuehren, carrierRelease]


    def getOperationIndex(self, stationKey, operation):
        opKey = -1
        for k, op in enumerate(self.stations[stationKey][0]):
            if op == operation:
                opKey = k
        return opKey


    def getOperationTime(self, stationKey, operation):
        opkey = self.getOperationIndex(stationKey, operation)
        if opkey == -1:
            return False
        else:
            return self.stations[stationKey][1][opkey]

    def getProductvarianteAsFullSizeArray(self, pv):
        retval = []
        for i in self.AllOperationsOrder:
            if i in pv:
                retval.append(int(1))           
            else:
                retval.append(int(0))
        return retval
    
        
    def stepUntilNextDecision(self):
        #Gibt folgendes zurück
        # 0 = Finished
        # 1 = Reward
        # 2 = actualState

        while self.productionFinished() == False:  
            if self.stepCnt >= self.iLastCheckBreakdowns:
                self.checkBreakdowns()
                self.iLastCheckBreakdowns = self.stepCnt+1

            if self.stepCnt >= self.iLastCheckOrderAssignment:
                self.assigningOrdersToEmptyCarriers()                
                self.iLastCheckOrderAssignment = self.stepCnt+1

            if self.stepCnt >= self.iLastCheckDecisionsNeeded:
                self.aadecisionStation, self.aadecisionWorkplan, self.aadecisionCarrier, self.aadecisionOp, self.aadecisionOrder = self.checkIfADecisionForACarrierIsNeeded()
                self.iLastCheckDecisionsNeeded = self.stepCnt+1

                temp = []
                for c in self.carrier:
                    temp.append(c[0])


            if len(self.aadecisionStation) > 0:
                templist = []
                for ok, o in (enumerate(self.aadecisionOrder)): 
                    templist.append(str(self.aadecisionOrder[ok]) + "-" + str(self.aadecisionOp[ok]))

                dublicate = [item for item, count in collections.Counter(templist).items() if count > 1]
                if len(dublicate)>1:
                    print("dublicate", dublicate)
                    ValueError("dublicate")

                ########################################################################
                # Prepare the necessary decisions for the agents
                ########################################################################

                self.popedStationKey    = self.aadecisionStation.pop()
                self.popedWorkplanKey   = self.aadecisionWorkplan.pop()
                self.popedCarrierKey    = self.aadecisionCarrier.pop()
                self.popedOrderKey      = self.aadecisionOrder.pop()
                self.popedOpKey         = self.aadecisionOp.pop()


                envState = self.getActualState()
                returnState = envState

                #                                              AgentId                    Workplan on Carrier    CarrierID             OpKey           OrderKey            Reward 
                return [False, self.stepCnt, returnState, [int(self.popedStationKey)+1, self.popedWorkplanKey, self.popedCarrierKey, self.popedOpKey, self.popedOrderKey, self.epiTempReward]]
            
            else:
                ########################################################################
                # Stepping one step further - executing decisions of the agents
                ########################################################################

                self.stepCnt += 1
                for k, carIdOnConveyor in (enumerate(self.conveyor)): 
                    if carIdOnConveyor != False:             
                        carKey = carIdOnConveyor-1       
                        lastCarUpdate = self.carrier[carKey][3]


                        if lastCarUpdate < self.stepCnt:
                            slotID = k + 1
                            nextSlotID = slotID +1
                           

                            self.carrier[carKey][5] = False         # CarrierShouldContinueMoving
                            if nextSlotID > len(self.conveyor):
                                nextSlotID = 1
                            


                            carAtStation = False 
                            for stationKey, station in enumerate(self.stations): 
                                if (int(slotID) == int(station[2])):
                                    carAtStation = True
                                    break 

                            
                            if carAtStation == True:
                                nextOp = self.carrier[carKey][0]
                                
                                if nextOp == False:
                                    self.carrier[carKey][3] = self.stepCnt      
                                    self.carrier[carKey][5] = True              # CarrierShouldContinueMoving

                                else:    
                                    if self.carrier[carKey][2] > 0:
                                        if self.carrier[carKey][2] >= self.getOperationTime(stationKey, nextOp):
             
                                            nextOp = self.getFollowingOperation(nextOp, self.carrier[carKey][9])
                                            if nextOp == False:
                                                orderPos = self.carrier[carKey][10]

                                                self.order[orderPos][3] = True                                                     
                                                self.carrier[carKey][9] = False         # 9 = ProductVariant    
                                                self.carrier[carKey][10]= False         # 10= orderPos                                                
                                                

                                            self.carrier[carKey][0] = nextOp            # Set the following operation
                                            self.carrier[carKey][2] = 0                 # Reset Progress
                                            self.carrier[carKey][3] = self.stepCnt      
                                            self.carrier[carKey][5] = True              # CarrierShouldContinueMoving

                                            # Stationsstatus anpassen
                                            self.stations[stationKey][5] = "inIdle"     # 5 = State - inIdle, inProduction 
                                            
                                        else:
                                            self.carrier[carKey][2] = self.carrier[carKey][2]+1     
                                            self.carrier[carKey][3] = self.stepCnt    

                                            self.carrierHistory[carKey][0].append(str(stationKey))
                                            self.carrierHistory[carKey][1].append(self.stepCnt)
                                            self.carrierHistory[carKey][2].append(nextOp)
                                    else:
                                        executed, releaseCarrier = self.shouldTheNextOperationExecuted(nextOp, stationKey, carKey)           
                                        if executed == True:

                                            self.carrier[carKey][7]    = False
                                            self.carrier[carKey][8]    = False

                                            self.carrier[carKey][2] = 1                 # 2 = OpProgress
                                            self.carrier[carKey][3] = self.stepCnt      # 3 = stepCnt-ActionVonStation


                                            self.carrierHistory[carKey][0].append(str(stationKey))
                                            self.carrierHistory[carKey][1].append(self.stepCnt)
                                            self.carrierHistory[carKey][2].append(nextOp)

                                            self.stations[stationKey][5] = "inProduction"   # 5 = State - inIdle, inProduction 
                                        else:
                                            self.carrier[carKey][3] = self.stepCnt      
                                            if releaseCarrier:
                                                self.carrier[carKey][5] = True              # CarrierShouldContinueMoving
                                            else:
                                                self.carrierHistory[carKey][0].append("B")         
                                                self.carrierHistory[carKey][1].append(self.stepCnt)
                                                self.carrierHistory[carKey][2].append("B")
                         

                            else:

                                self.carrier[carKey][3] = self.stepCnt      
                                self.carrier[carKey][5] = True              # CarrierShouldContinueMoving

                # Update Conveyor
                for a in range(2):
                    for k, carIdOnConveyor in (enumerate(self.conveyor)): 
                        if carIdOnConveyor != False: 
                            carKey = carIdOnConveyor-1
                            lastConveyorUpdate = self.carrier[carKey][6]    

                            if lastConveyorUpdate < self.stepCnt:

                                nextConveyorKey = k + 1
                                if nextConveyorKey > len(self.conveyor)-1:
                                    nextConveyorKey = 0

                                if self.carrier[carKey][5] == True and self.conveyor[nextConveyorKey] == False:
                                    self.conveyor[k]                 = False                
                                    self.conveyor[nextConveyorKey]   = carIdOnConveyor  
                                    self.carrier[carKey][6] = self.stepCnt                  
                                    if (self.stepCnt in self.carrierHistory[carKey][1]) == False:
                                        self.carrierHistory[carKey][0].append("T")        
                                        self.carrierHistory[carKey][1].append(self.stepCnt)
                                        self.carrierHistory[carKey][2].append("T")
                                elif self.carrier[carKey][5] == True and self.conveyor[nextConveyorKey] != False:
                                    if (self.stepCnt in self.carrierHistory[carKey][1]) == False:
                                        if self.carrier[carKey][0] == False:      
                                            self.carrierHistory[carKey][0].append("F") 
                                            self.carrierHistory[carKey][1].append(self.stepCnt)
                                            self.carrierHistory[carKey][2].append("F")
                                        else:
                                            self.carrierHistory[carKey][0].append("W") 
                                            self.carrierHistory[carKey][1].append(self.stepCnt)
                                            self.carrierHistory[carKey][2].append("W")

        returnState = self.getActualState() 
        return [True, self.stepCnt, returnState, [False, False, False, False, False, 0]] 
