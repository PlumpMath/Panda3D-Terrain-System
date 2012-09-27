from panda3d.core import NodePath,CollisionPolygon,CollisionNode,GeomVertexReader,BitMask32,Point3,BoundingSphere

import math

groundMask=BitMask32(0b1)


# from FenrirWolf via http://www.panda3d.org/forums/viewtopic.php?p=43705&sid=d5588e66bcedd9f7c7f51a3226ad890c
# modified by Craig Macomber
def rebuildGeomNodesToColPolys (incomingNode,relativeTo=None): 
    ''' 
    Converts GeomNodes into CollisionPolys in a straight 1-to-1 conversion 

    Returns a new NodePath containing the CollisionNodes 
    ''' 
    
    parent = NodePath('cGeomConversionParent') 
    for c in incomingNode.findAllMatches('**/+GeomNode'): 
        if relativeTo:
            xform=c.getMat(relativeTo).xformPoint
        else:
            xform=(c.getMat(incomingNode)*(incomingNode.getMat())).xformPoint
        gni = 0 
        geomNode = c.node() 
        for g in range(geomNode.getNumGeoms()): 
            geom = geomNode.getGeom(g).decompose() 
            vdata = geom.getVertexData() 
            vreader = GeomVertexReader(vdata, 'vertex') 
            cChild = CollisionNode('cGeom-%s-gni%i' % (c.getName(), gni)) 
            
            gni += 1 
            for p in range(geom.getNumPrimitives()): 
                prim = geom.getPrimitive(p) 
                for p2 in range(prim.getNumPrimitives()): 
                    s = prim.getPrimitiveStart(p2) 
                    e = prim.getPrimitiveEnd(p2) 
                    v = []
                    if e-s>2:
                        for vi in range (s, e): 
                            vreader.setRow(prim.getVertex(vi)) 
                            v.append (Point3(xform(vreader.getData3f())) )
                        colPoly = CollisionPolygon(*v) 
                        cChild.addSolid(colPoly) 

            n=parent.attachNewNode (cChild) 
            #n.show()
            
    return parent 


def _toCenterBox(b):
    if isinstance(b,BoundingSphere):
        return b.getCenter(),b.getRadius()
    a=b.getMin()
    b=b.getMax()
    center=(a+b)/2
    maxDist=max(max(abs(a[i]-center[i]),abs(b[i]-center[i])) for i in [0,1,2])
    return center,maxDist




def colTree (incomingNode): 
    '''
    assumes all passed nodes are collision nodes with no transforms
    
    returns produced oct-tree nodePath
    ''' 
    
    maxLevels=10
    b=incomingNode.getBounds()
    maxSize=b.getCenter().length()+b.getRadius()
    maxSize*=1.1
    levels=[{} for i in range(maxLevels)]
    top=NodePath(CollisionNode('colTreeTop'))
    levels[0][(0,0,0)]=top
    
    offset=Point3(maxSize,maxSize,maxSize)
    
    def fillNode(level,key):
        if level==0:
            assert key==(0,0,0)
        d=levels[level]
        cell=d.get(key)
        if cell is None:
            cell=NodePath(CollisionNode(str(key)))
            d[key]=cell
            if level>0:
                aboveKey=(key[0]/2,key[1]/2,key[2]/2)
                aboveCell=fillNode(level-1,aboveKey)
                cell.reparentTo(aboveCell)
        return cell
        
    for c in incomingNode.findAllMatches('**/+CollisionNode'): 
        cNode = c.node() 
        for i in range(cNode.getNumSolids()): 
            s=cNode.getSolid(i)
            b=s.getBounds()
            if not b.isEmpty():
                center,size=_toCenterBox(b)
                if size>0:
                    size=size/maxSize
                    level=math.log(1/size,2)
                    level+=3
                    level=min(level,maxLevels-1)
                    level=max(level,0)
                    level=int(math.ceil(level))
                    
                    center=center+offset
                    center=center/(maxSize*2)
                    
                    center=center*(2**level)
                    key=tuple(int(math.floor(center[i])) for i in [0,1,2])
                    cell=fillNode(level,key).node()
                    cell.addSolid(s)
    
    _mergeCol(top)          
    return top

def _mergeCol(node):
    """
    assumes all passed nodes are collision nodes
    
    merges solids for child nodes up to minimize nodes with few solids
    """
    mergeCount=10
    c=node.node()
    for n in node.getChildren():
        _mergeCol(n)
        cn=n.node()
        removed=False
        if n.getNumChildren()==0:
            num=cn.getNumSolids()
            if num<mergeCount:
                for i in xrange(num):
                    c.addSolid(cn.getSolid(i))
                n.removeNode()
                removed=True
        if not removed:
            numChildren=n.getNumChildren()
            num=cn.getNumSolids()
            if num==0 and numChildren==1:
                nn=n.getChild(0)
                nn.reparentTo(node)
                n.removeNode()
    