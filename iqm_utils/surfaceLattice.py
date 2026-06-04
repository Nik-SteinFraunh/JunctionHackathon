# -*- coding: utf-8 -*-
"""
Defines the surface code lattice
and some useful variables for the
Population Annealing decoder
 
Main classes: 
    
    -SurfaceCode(distance):
        Generates the data structure for a triangular code of given distance
        The distance should be odd
        
    - Qubit(index,x,y):
        Contains information about a qubit and its connectivity
    
    - Stabilizer(index,x,y, code_distance):
        Contains information about a stabilizer and its connectivity
        
Notation:
    Whenever there are two indices for the type of Pauli, 
    the first index
    represents X errors/ Z stabilizers/ X logical operator, 
    and the second index 
    represents Z errors/ X stabilizers/ Z logical operator.
    
    


Main functions of SurfaceCode:
    
    - generateErrorsBitFlip(p): generates bitflips with error rate p
    - generateErrorsDepolarizing(p): generates depolarizing noise at rate p
    - updateSyndrome(): updates the syndrome to be consistent with the error 
            and the correction
    - plot(): generates a plot of the lattice, errors and syndrome
    - H_bitflip(sigma,l): computes the hamiltonian for a given configuration 
        of spins sigma and for l=0,1
    - H_depolarizing(sigma,l_configuration : int): computes hamiltonian for 
        a given configuration of spins sigma and configuration of logical 
        operators in 0-3, corresponding to lx,lz:  [(0,0),(0,1),(1,0),(1,1)]
        *see https://arxiv.org/pdf/2303.01348.pdf

Main variables of Surface:
    
    - num_qubits: number of qubits
    - num_stabilizers: number of stabilizers of z type
    - error: array[num_qubits,2] of 1/0, bit-flip,phase-flip error configuration
    - syndrome: array[num_stabilizers,2] of 1/0 containing the current syndrome
    - correction: array[nq,2] of 1/0 containing the current correction
    - qubits: list[num_qubits] of Qubit() objects
    - stabilizers: list[2,num_stabilizers] of Stabilizer() objects
    
    - num_boundary: number of stabilizers in the boundary of Z type
    - boundary: list[2,num_boundary] of Stabilizer() objects for the boundary nodes
    
    - Ji: matrix[2,num_qubits,4] as described in the paper *
    - tiMatrix: matrix[2,num_qubits,num_stabilizers] describing the destabilizers T(s)
    - giMatrix: matrix[2,num_qubits,num_stabilizers] describing the stabilizers gi(s)
    - ti: array[2,num_qubits] referring to T(S) for the current syndrome S
    - li: array[2,num_qubits,4] containing the support of the logical operator
 


@author: PedroParrado
"""




import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import networkx as nx
import pymatching

class Qubit():
    def __init__(self, index: int, x : int, y : int):
        # the class qubit contains all information related to the qubit
        # including the position in the lattice, 
        # and the stabilizers to which it is connected
        # Coordinates x,y go from 0 to d-1
        
        # index of the qubit in the lattice
        self.index = index
        self.x = x
        self.y = y
        
        
        # list of indices of the stabilizers Z,X that connect to the qubit
        self.stabilizers = [[],[]]
        # stabilizers from the boundaries Z,X
        self.boundary = [[],[]]
        
        # set of destabilizers Z,X that contain this qubit
        self.ti = [set(),set()]
        
        # set of stabilizers Z,X that contain this qubit
        self.gi = [set(),set()]
        
        # set of logical operators X,Z that contain this qubit
        self.li = [set(),set()]

class Stabilizer():
    def __init__(self, index : int, x : int, y : int, 
                 code_distance : int, is_boundary : bool = False):
        # this class contains all relevant information related to a stabilizer
        # the coordinates refer to the bottom left corner of the stabilizer 
        # Coordinates x,y go from -1 to d
        
        self.index = index
        self.x = x
        self.y = y
        
        self.type = (x + y) %2 # 0: Z stabilizer, 1: X stabilizer
        
        self.parity = 0 # 0: even, 1: odd
        
        #if the stabilizer is a virtual stabilizer belonging to the boundary
        self.is_boundary = is_boundary
        
        
        # list of indices of the qubits that connect with this stabilizer
        self.qubits = []
               
        
        # representation of the plaquette
        
        xsquare = [x  ,x+1, x+1, x  ]
        ysquare = [y  ,y  , y+1, y+1]
        
        self.xqubits = []
        self.yqubits = []
        
        # we add only qubits in the range [0, codeDistance-1]
        for k in range(4):
            xk, yk = xsquare[k], ysquare[k] 
            if xk < code_distance and xk >= 0:
                if yk < code_distance and yk >= 0:
                    self.xqubits.append(xk)
                    self.yqubits.append(yk)
                    
        # the center of the stabilizer is 1/2 away from the corner
        self.xc = x + 0.5
        self.yc = y + 0.5
        
        # variables for the plot
        self.xplot = list(self.xqubits)
        self.yplot = list(self.yqubits)
        if len(self.xplot) < 4:
            self.xplot.append(self.xc)
            self.yplot.append(self.yc)
        
        
        # the ancilla is located in the middle
        self.xa = [x + 0.5]
        self.ya = [y + 0.5]
            
        self.nancilla = 1 # always 1 ancilla per stabilizer on surface code
        
                
    def plot(self,axis,                     # axis variable of the plot
             mark_stabilizer : bool = False, # highlights the stabilizer
             ancilla : bool = False,        # plot circles on ancillas
             colors = ['orange','turquoise'], # color pallete for stabilizers
             alpha : float = 0.7            # transparency of the polygons 
             ):
        
        # color of the stabilizer, for plotting purposes
        self.color = colors[self.type]  
        
        # adds a polygon to the axis
        xy = np.array([self.xplot,self.yplot]).transpose()
        if self.is_boundary: 
            plt.plot(self.xc,self.yc,'.',color = 'k',markersize = 16)
            plt.plot(self.xc,self.yc,'.',color = self.color,markersize = 13)
            plt.plot(self.xc,self.yc,'.',color = 'w',markersize = 3)
            return
        if mark_stabilizer:
            p = Polygon(xy, facecolor = "yellow", alpha = alpha)
            axis.add_patch(p)
            plt.plot(self.xc,self.yc,'.',color = 'k',markersize = 12)
            plt.plot(self.xc,self.yc,'.',color = 'yellow',markersize = 10)
        
        if ancilla:
            for i in range(self.nancilla):
                x,y = self.xa[i],self.ya[i]
                plt.plot(x,y,'.',color = 'k',markersize = 6)
                plt.plot(x,y,'.',color = self.color ,markersize = 4)
        
        p = Polygon(xy, facecolor = self.color, alpha = alpha)
        axis.add_patch(p)
        

class SurfaceCode():
    '''
    This class generates the data structure with information about the qubits, stabilizers,
    and their connectivity in a 488 triangular lattice. The input for the generator is 
    the code distance d
    '''
    def __init__(self, distance = 5):
        # initializes most variables of the code
        
        # if distance%2==0:
        #    raise Warning("The distance of the code should be an odd number")
        
        # side of the lattice
        self.distance = distance
        
        self.L = distance
        
        # list of Qubit objects
        self.qubits = []
        
        # dictionaries to find the qubits
        self.qubitIndextoCoord = {}
        self.qubitCoordtoIndex = {}
        
        # list of Stabilizer objects
        self.stabilizers = [[],[]]
        # dictionaries to find the stabilizers
        self.stabilizerIndextoCoord = {}
        self.stabilizerCoordtoIndex = {}
        
        
        # boundary stabilizers
        self.boundary= [[],[]]
        self.boundaryIndextoCoord = {}
        self.boundaryCoordtoIndex = {}
        
        # generate the square lattice
        self.generateLattice()
        
        ####################################################################
        # setting up other variables for QEC
        
        self.num_qubits = len(self.qubits)
        self.num_stabilizers = len(self.stabilizers[0])
        assert len(self.stabilizers[0]) == len(self.stabilizers[1]), "should have same number of Z and X stabilizers"
        
        self.num_boundary = len(self.boundary[0])
        
        self.num_ancilla = 2 * self.num_stabilizers
        
        # error configuration
        
        self.error = np.zeros((2,self.num_qubits))
        self.correction = np.zeros((2,self.num_qubits))
        self.syndrome = np.zeros((2,self.num_stabilizers))
        
        
        # variables for the decoders
        # we define them as empty arrays, will be filled during the decoding
        
        # matching graph
        self.graphs = self.generate_graphs()
        
        
        # indices: stab_type, qubit_index, logic_op_configuration
        self.Ji = np.zeros((2,self.num_qubits,4))
        self.ti = np.zeros((2,self.num_qubits))
        
        # the giMatrix contains the information about the support of stabs
        self.giMatrix = np.zeros((2,self.num_qubits,self.num_stabilizers))
        self.generateGiMatrix()
        
        # the tiMatrix contains all the information about the destabilizers:
        # it has a 1 in position x/y,q,s if the destabilizer T(s_x/y) has support 
        # on qubit q. This matrix does not depend on the syndrome
        self.tiMatrix = np.zeros((2,self.num_qubits,self.num_stabilizers))
        self.generateTiMatrix()
        
        # logical operators
        self.logic_op = np.zeros((2,self.num_qubits))
        
        # the logical X operator has support over the horizontal
        # the logical Z operator has support over the vertical
        for k in range(distance):
            # horizontal operator for X
            qindex = self.qubitCoordtoIndex[(k,0)]
            self.logic_op[0,qindex] = 1
            # vertical operator for Z
            qindex = self.qubitCoordtoIndex[(0,k)]
            self.logic_op[1,qindex] = 1
            
        # logic operator configurations
        self.li = np.zeros((2,self.num_qubits, 4))
        combinations = [(0,0),(1,0),(0,1),(1,1)]
        for k in range(4):
            lx = combinations[k][0]
            lz = combinations[k][1]
            # we add the logical operators corresponding to the combination
            self.li[0,:,k] += lx * self.logic_op[0,:]
            self.li[1,:,k] += lz * self.logic_op[1,:]
        # this should remain a binary variable
        self.li %= 2
        
    
    def generateLattice(self):
        ########################################
        ## Filling the qubits and stabilizers
        ########################################
        distance = self.distance
        
        #counters for stab. and qubits
        q_count = 0
        s_count = [0,0]
        # counters for the boundary nodes
        b_count = [0,0]
        
        # qubits on the square 0, distance-1        
        for y in range(distance):
            for x in range(distance):
                # we add a new qubit
                self.qubits.append(Qubit(q_count,x,y))
                # and update the coordinates in the dictionaries
                self.qubitIndextoCoord[q_count] = (x,y)
                self.qubitCoordtoIndex[(x,y)] = q_count
                # add 1 to the qubit count
                q_count += 1
                
            
        # stabilizers on the square -1, distance
        for y in range(-1, distance):
            for x in range(-1, distance):
                # first we check the stabilizer type, Z or X
                stab_type = (x+y)%2
                
                # we find if the stabilizer is a boundary node
                is_boundary = False
                # vertical boundaries for Z stabilizers 
                if stab_type == 0 and (x<0 or x == distance-1):
                    is_boundary = True
                # horizontal boundaries for X stabilizers 
                if stab_type == 1 and (y<0 or y == distance-1):
                    is_boundary = True
                    
                if is_boundary:
                    index = b_count[stab_type]
                    # we create a new boundary node
                    self.boundary[stab_type].append(Stabilizer(
                                    index = index,
                                    x = x, y = y,
                                    code_distance = distance,
                                    is_boundary = is_boundary))
                    # update the dictionaries to find it
                    self.boundaryIndextoCoord[(stab_type,index)] = (x,y)
                    self.boundaryCoordtoIndex[(x,y)] = (stab_type,index)
                    # add one to the counter
                    b_count[stab_type] += 1
                else:
                    index = s_count[stab_type]
                    # we create a new boundary node
                    self.stabilizers[stab_type].append(Stabilizer(
                                    index = index,
                                    x = x, y = y,
                                    code_distance = distance,
                                    is_boundary = is_boundary))
                    # update the dictionaries to find it
                    self.stabilizerIndextoCoord[(stab_type,index)] = (x,y)
                    self.stabilizerCoordtoIndex[(x,y)] = (stab_type,index)
                    # add one to the counter
                    s_count[stab_type] += 1
        # with that, we have created all stabilizers
                    
        ##################################################
        # filling the connectivity of the qubits and stabilizers
        for stab_type in range(2):
            for stabilizer in self.stabilizers[stab_type]:
                # coordinates of the neighbors of the stabilizer
                xq, yq = stabilizer.xqubits, stabilizer.yqubits
                
                for k in range(len(xq)):
                    # we find the index of the qubit
                    qindex = self.qubitCoordtoIndex[(xq[k],yq[k])]
                    sindex = stabilizer.index
                    # update the connectivity of the qubit:
                    self.qubits[qindex].stabilizers[stab_type].append(sindex)
                    
                    # update the set of generators
                    self.qubits[qindex].gi[stab_type].add(sindex)
                    
                    # update the connectivity of the stabilizer
                    stabilizer.qubits.append(qindex)
                    
        # repeat for the boundary nodes    
                
        for stab_type in range(2):
            for bound in self.boundary[stab_type]:
                # coordinates of the neighbors of the stabilizer
                xq, yq = bound.xqubits, bound.yqubits
                
                for k in range(len(xq)):
                    # we find the index of the qubit
                    qindex = self.qubitCoordtoIndex[(xq[k],yq[k])]
                    bindex = bound.index
                    # update the connectivity of the qubit:
                    self.qubits[qindex].boundary[stab_type].append(bindex)
                                        
                    # update the connectivity of the stabilizer
                    bound.qubits.append(qindex)
        
        
    def generateTiMatrix(self):
        # fills the tiMatrix with the support of the Destabilizers 
        
        self.tiMatrix =np.zeros((2,self.num_qubits,self.num_stabilizers))
        
        # we fill it by going through each stabilizer and adding 
        # the corresponding de-stabilizer to the tiMatrix
        
        # for the Z stabilizers, the destabilizers are horizontal chains
        # for the X stabilizers, the destabilizers are vertical chains
        
        for stab_type in range(2):
            for stabilizer in self.stabilizers[stab_type]:
                sindex = stabilizer.index
                # first we find the coordinates of the stabilizer
                xs,ys = self.stabilizerIndextoCoord[(stab_type,sindex)]
                
                # now we trace a line from the boundary to xs or ys
                maxk = (xs+1,ys+1)[stab_type]
                for k in range(maxk):
                    # we ensure the y/x coordinate is within the range [0,d] using max()                    
                    if stab_type == 0:
                        # horizontal line
                        xy = (k, max(0,ys))
                    else: 
                        # vertical line
                        xy = (max(0,xs), k)
                    qindex = self.qubitCoordtoIndex[xy]
                    
                    # the destabilizer sindex has support on qubit qindex
                    self.tiMatrix[stab_type, qindex, sindex] =1 
                        
                            
        # now tiMatrix should contain all information about the destabilizers        
        return
                
 
    def generateGiMatrix(self):
        # fills the Gimatrix with the support of the stabilizers        
        
        self.giMatrix = np.zeros((2,self.num_qubits,self.num_stabilizers))  
        
        # we fill it by going through each stabilizer and adding 
        # the corresponding stabilizer to the giMatrix
        
        for stab_type in range(2):
            for stabilizer in self.stabilizers[stab_type]:
                sindex = stabilizer.index
                
                for qubit in stabilizer.qubits:
                    self.giMatrix[stab_type, qubit, sindex] = 1 
                
        # now giMatrix should contain all information about the stabilizers        
        return
        
    
    def checkTiMatrix(self,stab_index : int = 0, stab_type : int = 0):
        # debugging function to check the TiMatrix
        
        self.error = self.tiMatrix[stab_type % 2, :, stab_index % self.num_stabilizers]
        self.updateSyndrome()
        self.plot()       
        
    
    def generateErrorsBitFlip(self,p = 0.09):
        # generates an error configuration by introducing bitflips on 
        # each qubit with probability p
        
        self.error = np.zeros((2,self.num_qubits))
        self.correction = np.zeros((2,self.num_qubits))
        counter = 0
        # we generate the random numbers
        r = np.random.rand(self.num_qubits)
        
        for qi in range(self.num_qubits):
            if r[qi] < p:
                self.error[0,qi] = 1
                counter += 1
        # update syndrome and return error count
        self.updateSyndrome()
        return counter
    
    def generateErrorsDepolarizing(self,p = 0.09):
        # generates an error configuration by introducing bitflips on 
        # each qubit with probability p
        
        self.error = np.zeros((2,self.num_qubits))
        self.correction = np.zeros((2,self.num_qubits))
        counter = 0
        # we generate the random numbers
        r = np.random.rand(self.num_qubits)
        
        for qi in range(self.num_qubits):
            if r[qi] < p:
                # if an error happened, we pick a random pauli
                pauli = np.random.randint(0,3)

                if pauli in [0,2]:
                    self.error[0,qi] = 1
                if pauli in [1,2]:
                    self.error[1,qi] = 1
                    
                counter += 1
        # update syndrome and return error count
        self.updateSyndrome()
        return counter
                
    
    
    def generate_graphs(self):
        # generates two graphs for the Z,X stabilizers of the code
        
        
        graphs = [nx.Graph(),nx.Graph()] 
        
        # note: we shouldn't need these since each edge corresponds to a qubit
        # edgeDict = [{},{}]
        # edgesinDict = [{},{}]
        # edgecount = [0,0]
         
        # one node per stabilizer and boundary 
        #num_detectors = self.num_stabilizers +len(self.boundary[0]) 
        
        for stab_type in range(2):
            for k in range(self.num_stabilizers): 
                graphs[stab_type].add_node(k)
            for k in range(len(self.boundary[stab_type]) ): 
                index = k + self.num_stabilizers
                graphs[stab_type].add_node(index, is_boundary = True)
    
        
        # now we add the links
        for stab_type in range(2):
            for q in self.qubits:
                ns = len(q.stabilizers[stab_type]) 
                
                # we add a link between all neighboring stabilizers (should be 2)
                for i in range(ns-1):
                    for j in range(i+1,ns): 
                        st = stab_type
                        e1,e2 = q.stabilizers[st][i], q.stabilizers[st][j]

                        graphs[stab_type].add_edge(e1,e2,fault_ids= q.index)  
                            
                # now we add the connections with the boundary
                ns = len(q.stabilizers[stab_type]) 
                nb = len(q.boundary[stab_type])
                for i in range(nb):
                    for j in range(ns):  
                        ib = q.boundary[stab_type][i]
                        js = q.stabilizers[stab_type][j]   
                    
                        e1,e2 = ib + self.num_stabilizers, js
                        
                        graphs[stab_type].add_edge(e1,e2,fault_ids= q.index) 
        
        return graphs    
        
    def mwpm_decoder(self, apply_correction = True):
        # takes a code with errors and applies a correction 
        
        correction = np.zeros((2,self.num_qubits))
        for stab_type in range(2):
            
            # for the matching, we need a value (0) for the syndrome on the 
            # boundary nodes 
            syndrome = np.array(list(list(self.syndrome[stab_type])
                                      +[0]*len(self.boundary[stab_type])))
             
        
            # matching 
            match_graph = pymatching.Matching.from_networkx(self.graphs[stab_type])
            correction[stab_type,:] = match_graph.decode(syndrome)  
        
        if apply_correction:
            self.correction = correction
        return correction
    
    
    
    def updateSyndrome(self, updateSAvariables = True, count_correction = True):
        # updates the value of the syndrome and the values of the variables ti and Ji
        
        # syndrome = np.zeros((2,self.num_stabilizers))
        
        for stab_type in range(2):
            for stabilizer in self.stabilizers[stab_type]:
                stab_index = stabilizer.index
                par = 0
                # every qubit with an error in x/z flips stabilizers z/x
                for qubit in stabilizer.qubits:
                    par += self.error[stab_type,qubit]
                    if count_correction:                        
                        par += self.correction[stab_type,qubit]
                self.syndrome[stab_type, stab_index ] = par % 2
                    
        if updateSAvariables:
            self.updateTi()
            self.updateJi()
        return    
        
    
    
    def updateTi(self):
        # updates the value of ti depending on the current syndrome
        
        self.ti = np.zeros((2,self.num_qubits))
        
        # we loop over stabilizers, and add the destabilizers of the 
        # excited stabilizers to ti
        for stab_type in range(2):
            for stab in range(self.num_stabilizers):
                # if the stabilizer is excited, we add the destabilizer
                if self.syndrome[stab_type, stab] > 0:
                    self.ti[stab_type,:] += self.tiMatrix[stab_type,:,stab]
        
        # ti should be binary
        self.ti %= 2
        return
        
    def updateJi(self):
        # updates the value of Ji,l = (1 - 2 * li * l ) * ( 1 - 2 * ti)
        self.Ji = np.zeros((2, self.num_qubits, 4))
    
        for stab_index in range(2):
            for combo in range(4):
                # each combo corresponds to a combination of logical operators:
                # lx,lz = (0,0), (1,0), (0,1), (1,1)
                
                logic_factor = (1 - 2 * self.li[stab_index, :, combo] )  
                ti_factor = ( 1 - 2 * self.ti[stab_index, :])
                self.Ji[stab_index, :, combo ] = logic_factor * ti_factor
        return
    
    def H_bitflip(self, sigma,logic_operator : int = 0, stab_type : int = 0): 
        '''
        Function to compute the Hamiltonian for the bitflip error model 
        H = sum_i(  -Ji prod_(j in Bi)( sigma_j) )
        
        Input: 
            sigma: array of size num_stabilizers, values +1/-1
            l: integer for logical operator, values 1/0 
        Output: 
            value of H, float
        '''
        h = 0
        
        # loop over qubits
        for qi in range(self.num_qubits):
            # aux for the product
            pr = 1
            # we only loop over the Z stabilizers [index=0]
            for stab in self.qubit[qi].stabilizers[stab_type]:
                pr *= sigma[stab]
            # the third index in Ji corresponds to the logic_operator combination
            # lx,lz = [(0,0), (1,0), (0,1), (1,1)]
            # if stab_type == 1, then the combinations with lz = 1 are 2 and 3
            l_op = logic_operator * ( 1 + stab_type )
            h += - self.Ji[stab_type, qi, l_op] * pr
        
        return h
        
    def H_depolarizing(self, sigma, logic_operator : int = 0):
        '''
        Computes the hamiltonian for a given spin configuration and a 
        combination of the logical operators, logical_operators = [Lx,Lz]
        following https://arxiv.org/pdf/2303.01348.pdf  (Eq.23)
        
        The spin configuration is a matrix of dimensions (2,num_stabilizers),
        where the second dimension corresponds to the two paulis X,Z
    
        The information on the logical operators can be introduced as 
        - an integer op_configuration in [0,1,2,3] representing which 
          of the four combinations of logical operators is computed
        - a pair of integers [lx,lz], each being 0,1, representing the actual 
          state of each logical operator
          
        The function returns a float with the value of the hamiltonian
        '''
        
    
        # the first two terms in the Hamiltonian can be computed within
        # the functions for bitflips
        
        combinations = [(0,0),(1,0),(0,1),(1,1)]
        lx,lz = combinations[logic_operator]
        
        Hx = self.H_bitflip(sigma[0,:],lx)
        Hz = self.H_bitflip(sigma[1,:],lz) 
        
        
        # now we compute the mixed term from eq. 26 
    
        Hy = 0
        for i in range(self.num_qubits):
            # product of spins
            product = 1
            for stab_type in range(2):
                for s in self.qubits[i].stabilizers[stab_type]:
                    product*= sigma[stab_type,s]
            # product of Ji
            Jpr = self.Ji[0,i,logic_operator] * self.Ji[1,i,logic_operator]
            Hy += - Jpr *product
            
        # the final hamiltonian is the sum of all terms
        return Hx + Hy + Hz
        
             
            
    
    def sigmaToCorrection(self,sigma,logical,applyCorrection=True):
        # for a given spin configuration sigma in [+1,-1]*ns
        # and logical operation in [0,1]
        # computes the correction using eq.12 in
        # https://arxiv.org/pdf/2303.01348.pdf
        
        # adds gi for all sigmas with value -1
        assert len(sigma)%self.num_stabilizers ==0, "Sigma should be of length "+str(self.num_stabilizers)
        
        c = np.zeros((2,self.num_qubits))
        
        # we add stabilizers corresponding to the sigma's with value -1
        # we distinguish between two types of input, for bitflip or depolarizing
        if len(sigma) == self.num_stabilizers:
            # the input only contains Z stabilizers
            for stab in range(self.num_stabilizers):
                # we add the stabilizer if sigma[stab] == -1
                if sigma[stab]<0:
                    c += self.giMatrix[0, : , stab]
        else:
            # the input should contain a matrix of size (2,num_stabilizers)
            for stab_type in range(2):
                for stab in range(self.num_stabilizers):
                    # we add the stabilizer if sigma[stab] == -1
                    if sigma[stab_type,stab] < 0 :
                        c += self.giMatrix[stab_type, :,stab]
            
                
        # we add the destabilizers
        c+= self.ti
        
        # we add the logical operation 
        c+= self.li[:,:,logical]
        
        # the correction should be binary, so we take modulo 2
        c%= 2
        if applyCorrection:
            self.correction = c
        return c
            
    
    def checkCorrection(self, correction = []):
        # checks if a given correction leads to a logical error
        # if no correction was received as input, uses the correction 
        # that is already stored in self.correction
        
        if len(correction)>0:
            c = correction
        else:
            c = self.correction
        
        # we add the error and the correction
        # and multiply the support of the line perpendicular
        # to the logical operators
        parX = (self.error[0,:]+c[0,:])%2 *self.li[1,:,3]
        parZ = (self.error[1,:]+c[1,:])%2 *self.li[0,:,3]
        
        # then we compute the parity 
        return np.sum(parX)%2, np.sum(parZ)%2
        
    
    def checkSigma(self,sigma):
        # checks if sigma leads to a logical operator or not for all 
        # values of the logical operators lx,lz
        
        solved =[]
        for logic_op in range(4):
            c = self.sigmaToCorrection(sigma, logic_op, applyCorrection=False)
            solved.append(self.checkCorrection(c))
        return solved
        
    def decoderCheck(self):
        # checks which error class corresponds to a logical error
        # returns the error class for T(S), and for T(S)+li
        # if the parity is 0, it means it corrects the error
        
        
        # parity of error +T(S)
        correction = (self.error+self.ti)%2
        
        solved = []
        for logic_class in range(4):
            # support of the correction on the logical op
            l_sup = correction * self.li[:,:,logic_class]
            # parity of that support on each operator:
            px,pz = np.sum(l_sup[0,:])%2, np.sum(l_sup[1,:])%2
            
            # if any of those is not corrected, we consider it a fail
            solved.append( max(px,pz )) 
            
        return solved 
        
        ############# old code:  

    def plot(self, figsize = [],
             mark_qubit : int = -1, mark_stabilizer : int = -1, 
             ancilla : bool = False,
             boundary : bool = True,
             show : bool = True, 
             stab_index : bool = False,
             qubit_size : float = 4,
             error_size : float = 8,
             error_color = 'red',
             correction_color = "green",
             correction_size : float = 5, 
             error_markers = ["_","|"],
             stab_alpha : float = 0.5,
             stab_colors = ['orange', 'teal'],
             matching_graph  = [False,False],
             edge_width : float = 1.7
             ):
        # plots the lattice
        if figsize:
            fig,ax = plt.subplots(figsize = figsize)
        else:
            fig,ax = plt.subplots(figsize = (self.distance,self.distance))
            
        # plotting the qubits
        for q in self.qubits:
            plt.plot(q.x,q.y,'.',markersize = qubit_size,color = 'k')
            for s_type in range(2):
                e = self.error[s_type, q.index]
                c = self.correction[s_type, q.index]
                # displaying errors with different markers
                if e:
                    plt.plot(q.x,q.y,error_markers[s_type],
                             markersize=error_size*1.1,color = 'k')
                    plt.plot(q.x,q.y,error_markers[s_type],
                             markersize=error_size,color = error_color)
                if c:
                    plt.plot(q.x,q.y,error_markers[s_type],
                             markersize=correction_size*1.1,color = 'k')
                    plt.plot(q.x,q.y,error_markers[s_type],
                             markersize=correction_size,color = correction_color)
                    
            # mark this qubit for debugging purposes
            if q.index==mark_qubit:                
                plt.plot(q.x,q.y,'.',markersize=8,color = 'k')
                plt.plot(q.x,q.y,'.',markersize=6,color = 'orange')
                for s_type in range(2):
                    for si in q.stabilizers[s_type]:
                        s = self.stabilizers[s_type][si]
                        plt.plot(s.xc,s.yc,'.',markersize=12,color = 'k')
                        plt.plot(s.xc,s.yc,'.',markersize=8,color = 'yellow')
                        s.plot(ax,1)
            
        # plotting the stabilizers
        for s_type in range(2):
            for s in self.stabilizers[s_type]:
                s.plot(ax,self.syndrome[s_type,s.index],ancilla = ancilla,
                        colors=stab_colors, alpha = stab_alpha)
                
                # mark this stabilizer for debugging purposes
                if s.index == mark_stabilizer:
                    plt.plot(s.xc,s.yc,'.',markersize=12,color = 'k')
                    plt.plot(s.xc,s.yc,'.',markersize=8,color = 'yellow')
                    s.plot(ax,1)
                    
                    for qi in s.qubits:
                        q = self.qubit[qi]
                        plt.plot(q.x,q.y,'.',markersize=8,color = 'k')
                        plt.plot(q.x,q.y,'.',markersize=6,color = 'orange')
                if stab_index:
                    plt.plot(s.xc,s.yc,marker = "$"+str(s.index)+"$",markersize=12,color = 'k')
                
        if boundary:
            for s_type in range(2):
                for s in self.boundary[s_type]:
                    s.plot(ax)
                    if stab_index:
                        plt.plot(s.xc,s.yc,marker= "$"+str(s.index)+"$",markersize=12,color = 'k')
                
        self.plot_graphs(stab_colors, edge_width, selection = matching_graph)
            
        plt.axis("off")
        ax.set_xlim([-1.1,self.L+1.1])
        ax.set_ylim([-1.1,self.L+1.1])
        if show:
            plt.show()
            
        return fig,ax
        



    
    def plot_graphs(self, colors =  ['orange', 'teal'],
                    edge_width = 1.7, selection = [True,True]):
        # plots the matching graphs        

        for stab_type in range(2):
            if selection[stab_type]:
                x = []
                y = [] 
                
                # coordinates of the nodes (stabs and boundaries)
                for s in range(self.num_stabilizers):
                    x.append(self.stabilizers[stab_type][s].xc)
                    y.append(self.stabilizers[stab_type][s].yc) 
            
                for s in range(len(self.boundary[stab_type])):
                    x.append(self.boundary[stab_type][s].xc)
                    y.append(self.boundary[stab_type][s].yc) 
            
                # edges in the graph
                e = self.graphs[stab_type].edges
                for edge in e:
                    i0,i1 = edge  
                    x0,y0 = x[i0],y[i0]  
                    x1,y1 = x[i1],y[i1]  
                    
                    # we plot the edge
                    plt.plot([x0,x1],[y0,y1], color = 'k',
                             linewidth = edge_width * 1.1 )
                    plt.plot([x0,x1],[y0,y1], color = colors[stab_type],
                             linewidth = edge_width )
                








