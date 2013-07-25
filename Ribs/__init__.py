from .move import rotation#, alignment
from Profile import Profile2D, XFoil
import numpy
from numbers import Real


class rib(object):
    """docstring for rib"""

    def __init__(self, profile="", startpoint=numpy.array([0, 0, 0]), arcang="", aoa="", zrot="", glide="", name="unnamed rib",aoaabs=False,startpos=0.):
        self.name = name
        if isinstance(profile, list):
            self.profile2D = Profile2D(profile, name=name)

        self._aoa=(aoa,aoaabs)
        self.glide=glide
        self.arcang=arcang
        self.zrot=zrot
        
        self.ReCalc()


    def Align(self, points):
        return self._pos(self._rot(points))
    
    def SetAOA(self,aoa):
        try:
            self._aoa=(aoa[0],bool(aoa[1]))
        except:
            self._aoa=(float(aoa),False)#default: relative aoa
    def GetAOA(self):
        return dict(zip(["rel","abs"],self.aoa))###return in form: ("rel":aoarel,"abs":aoa)
    
    
    def ReCalc(self):
        #recalc aoa_abs/rel
        #Formula for aoa rel/abs: ArcTan[Cos[alpha]/gleitzahl]-aoa[rad];
        diff=numpy.arctan(numpy.cos(self.arcang)/self.glide)
        #aoa->(rel,abs)
        self.aoa[self._aoa[1]]=self._aoa[0]
        self.aoa[1-self._aoa[1]]=diff-self._aoa[0]
        
        self._rot=rotation(self.aoa[1],self.arcang, self.zrot)
        self.profile3D=self.Align(self.profile2D.Profile)
    
    AOA=property(GetAOA(),SetAOA())
        
