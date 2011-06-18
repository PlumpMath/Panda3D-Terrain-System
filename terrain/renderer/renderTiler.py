import math

from renderer import RenderNode
from terrain.bakery.bakery import loadTex
from terrain.meshManager import meshManager

from panda3d.core import *
from direct.task.Task import Task

from terrain import tileUtil

from terrain.bakery.bakery import FixedBakery,FixWrapped


class RenderNodeTiler(NodePath):
    def __init__(self,renderTileSource,tileSize,focus,forceRenderedCount=2,maxRenderedCount=4):
        NodePath.__init__(self,"RenderNodeTiler")        
        self.tileSize=tileSize
        self.forceRenderedCount=forceRenderedCount
        self.maxRenderedCount=maxRenderedCount
        self.focus=focus
        
        self.renderTileBakery=renderTileSource
        
        cacheSize=maxRenderedCount
        x,y=self.focuseLoc()
        self.bakeryManager=tileUtil.NodePathBakeryManager(self,
            self.renderTileBakery,tileSize,
            forceRenderedCount,maxRenderedCount,cacheSize,
            x,y)
        
        # Add a task to keep updating the terrain
        taskMgr.add(self.updateTiles, "updateTiles")
    def focuseLoc(self):
        p=self.focus.getPos(self)
        return p.getX(),p.getY()
    
    def updateTiles(self,task):
        self.bakeryManager.updateCenter(*self.focuseLoc())
        return Task.cont 
            
    def height(self,x,y):
        return self.bakeryManager.getTile(x,y).height(x,y)



class RenderTileBakery(FixedBakery):
    """
    A class the wraps a bakery to produce RenderTiles instead of baked tiles
    """
    def __init__(self,bakery,tileSize,meshManager):
        self.bakery=FixWrapped(bakery,tileSize)
        self.hasTile=bakery.hasTile
        self.meshManager=meshManager
        
    def getTile(self, x, y):
        return RenderTile(self.bakery.getTile(x, y),self.meshManager)
    
    def asyncGetTile(self, x, y, callback, callbackParams=()):
        self.bakery.asyncGetTile(x, y, self._asyncTileDone, (callback,callbackParams))
        
    def _asyncTileDone(self,tile,callback,callbackParams):
        callback(RenderTile(tile,self.meshManager),*callbackParams)

class RenderTile(NodePath):
    """
    Currently this calss gets it's height(x,y) method added to it by a GroundFactory
    
    It could sample its height map instead, but it does not know the height scale.
    """
    def __init__(self,bakedTile,meshManager):
        """
        node = the renderNode this is for
        """
        self.bakedTile=bakedTile
        
        NodePath.__init__(self,"renderTile")
        self.setPythonTag("subclass", self)
        
        
        
        self.tileScale=bakedTile.scale
        
        # Save a center because some things might want to know it.
        self.center=Vec3(bakedTile.x+self.tileScale/2.0,bakedTile.y+self.tileScale/2.0,0)
        
        renderMaps=bakedTile.renderMaps
        
        # generate meshes on it
        x=bakedTile.x
        y=bakedTile.y
        x2=x+bakedTile.scale
        y2=y+bakedTile.scale
        
        
        self.meshes=meshManager.makeTile(x,y,x2,y2,self)
        if self.meshes is None:
            self.meshes=NodePath("EmptyMeshes")
        self.meshes.reparentTo(self)
        
    def update(self,focus):
        self.meshes.update(focus)
    
    def sampleMap(self,mapName,x,y):
        map=self.bakedTile.renderMaps[mapName]
    
        peeker=map.tex.peek()
        tx=(x-self.bakedTile.x)/self.tileScale
        ty=(y-self.bakedTile.y)/self.tileScale
        
        sx=peeker.getXSize()
        sy=peeker.getYSize()
        px=(sx*tx)
        py=(sy*ty)
        
        
        #u=math.floor(px)/sx
        #v=math.floor(py)/sy
        fu=px-math.floor(px)
        fv=py-math.floor(py)
        #u2=math.floor(px+1)/sx
        #v2=math.floor(py)/sy
        px=math.floor(px)
        py=math.floor(py)
        
        #peeker.lookup(c,u,v)
        def getH(x,y):
            c=Vec4()
            peeker.lookup(c,x/sx,y/sy)
            return c
        h=(getH(px+1,py+1)*fu+getH(px,py+1)*(1-fu))*fv+(getH(px+1,py)*fu+getH(px,py)*(1-fu))*(1-fv)
        
        #peeker.filterRect(c,px/sx,py/sy,px/sx,py/sy)
        return h
    
