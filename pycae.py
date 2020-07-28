import re

import OCC.BRep
import OCC.TopoDS
import OCC.TopExp
import OCC.BRepTools
import OCC.BRepPrimAPI

# Rename to snake_case and CamelCase respectively
camelcase_pattern = re.compile(r'(^|_)([a-z])'), lambda match: match.group(2).upper()
snakecase_pattern = re.compile(r'[A-Z]'), lambda match: "_%s" % match.group(0).lower()
rename_camelcase = lambda s: camelcase_pattern[0].sub(camelcase_pattern[1], s)
rename_snakecase = lambda s: s[0].lower() + snakecase_pattern[0].sub(snakecase_pattern[1], s[1:])

# Functions that return OCC.TopoDS.TopoDS_Face and OCC.TopoDS.topods_Face for "face"
get_occ_class = lambda nm: getattr(OCC.TopoDS, "TopoDS_" + rename_camelcase(nm))
get_occ_cast = lambda nm: getattr(OCC.TopoDS, "topods_" + rename_camelcase(nm))

# All OCC topology types as string
topology_types = "compound", "comp_solid", "solid", "shell", "face", "wire", "edge", "vertex", "shape"
# All OCC topology types as native class
topology_occ_classes = list(map(get_occ_class, topology_types))
# All OCC topology types as a casting function
topology_occ_casts = list(map(get_occ_cast, topology_types[:-1]))
# Topology types that have an underlying geometry and function to obtain it
topology_geometries = {"vertex": ("point", OCC.BRep.BRep_Tool.Pnt), "edge": ("curve", OCC.BRep.BRep_Tool.Curve), "face": ("surface", OCC.BRep.BRep_Tool.Surface)}
# Mapping from integer (TopAbs_ShapeEnum) to topology string
topology_type_ids = dict((__,_) for _,__ in enumerate(topology_types))

# Some other enumerations
forward, reversed = 0, 1

class topology_exception(Exception): pass


class shape(object):

    """Base class for all topological entities. Basically this corresponds to TopoDS_Shape"""

    def __init__(self, occ_data):
        
        """Initialize based on an underlying native class. Note that the shapetype is obtained
        and casted to the appropriate subclass. This ensures relevant methods can be called
        also when generic shapes are returned, for example by TopExp_Explorer"""
        
        self.occ_data = topology_occ_casts[occ_data.ShapeType()](occ_data)

    @staticmethod
    def create(occ_data):
        
        """Find the appropriate subtype of shape, (e.g vertex) and constructs"""
        
        return globals()[topology_types[occ_data.ShapeType()]](occ_data)
        
    def explore(self, topology_type=None, avoid=None):
    
        """Helper function to explore underlying topology. The most suitable explorer is
        determined automatically. Wires are explored in order"""
        
        if topology_type is not None:
            if self.topology_type >= topology_type.topology_type:
                typenames = tuple(map(topology_types.__getitem__, (topology_type.topology_type, self.topology_type)))
                raise topology_exception("'%s' > '%s'" % typenames)
                
        if avoid is not None:
            if self.topology_type >= avoid.topology_type:
                raise topology_exception("'%s' > '%s' % (avoid.topology_type, self.topology_type)")
                
        if self.topology_type == "wire":
            exp = OCC.BRepTools.BRepWire_Explorer(self.occ_data)
            def _():
                while exp.More():
                    yield edge(exp.Current()) if topology_type != vertex else vertex(exp.CurrentVertex())
                    exp.Next()
            return _()
            
        else:
            if topology_type is None:
                exp = OCC.TopoDS.TopoDS_Iterator(self.occ_data)
            elif avoid is not None:
                exp = OCC.TopExp.TopExp_Explorer(self.occ_data, topology_type.topology_type, avoid.topology_type)
            else:
                exp = OCC.TopExp.TopExp_Explorer(self.occ_data, topology_type.topology_type)
            def _():
                while exp.More():
                    yield shape.create(exp.Current() if hasattr(exp, 'Current') else exp.Value())
                    exp.Next()
            return _()
            

def make_function(attr):
    def _(self, *args, **kwargs):
        return getattr(self.occ_data, attr)(*args,**kwargs)
    return _
    
# For all topology types, construct a class that subclasses `shape`
for t in topology_types:
    # Create the type
    tt = type(t, (shape,), {})
    
    # Assign a numeric (TopAbs_ShapeEnum) identifier to the type
    tt.topology_type = topology_type_ids[t]
    
    # See if there is an underlying geometry and create method to access
    geom, fn = topology_geometries.get(t, (0,0))
    if geom:
        setattr(tt, geom, (lambda func: lambda self: func(self.occ_data))(fn))
    
    # Add all methods of the OCC type as well and rename to snake_case
    # convention. This still requires a lot of work
    for nm in dir(topology_occ_classes[tt.topology_type]):
        if not nm.startswith('__'):
            setattr(tt, rename_snakecase(nm), make_function(nm))
            
    # Register the class in the global namespace
    globals()[t] = tt    
    

# For the primitive module create simple functions that return shape immediately
for nm in dir(OCC.BRepPrimAPI):
    if nm.startswith("BRepPrimAPI_Make") and not nm.endswith("_swigregister"):
        globals()[rename_snakecase(nm.split('_')[1])] = (lambda builder: lambda *args, **kwargs: shape.create(getattr(OCC.BRepPrimAPI, builder)(*args, **kwargs).Shape()))(nm)
