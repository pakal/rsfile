# Create ctypes wrapper code for abstract type descriptions.
# Type descriptions are collections of typedesc instances.

import typedesc, sys, os
import textwrap
import struct, ctypes

# This should be configurable
ASSUME_STRINGS = True

try:
    set
except NameError:
    from sets import Set as set

try:
    sorted
except NameError:
    def sorted(seq, cmp):
        seq = list(seq)
        seq.sort(cmp)
        return seq

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

# This is what GCCXML uses as size of varsized arrays in structure
# field:
GCCXML_NOSIZE = "0x" + "f" * ctypes.sizeof(ctypes.c_long) * 4

# XXX Should this be in ctypes itself?
ctypes_names = {
    "bool": "c_bool",
    "unsigned char": "c_ubyte",
    "signed char": "c_byte",
    "char": "c_char",

    "wchar_t": "c_wchar",

    "short unsigned int": "c_ushort",
    "short int": "c_short",

    "long unsigned int": "c_ulong",
    "long int": "c_long",
    "long signed int": "c_long",

    "unsigned int": "c_uint",
    "int": "c_int",

    "long long unsigned int": "c_ulonglong",
    "long long int": "c_longlong",

    "double": "c_double",
    "float": "c_float",

    "long double": "c_longdouble",

    # Hm...
    "void": "None",
}

if not hasattr(ctypes, "c_longdouble"):
    ctypes_names['long double'] = 'c_double' # only since python2.6

################

def storage(t):
    # return the size and alignment of a type
    if isinstance(t, typedesc.Typedef):
        return storage(t.typ)
    elif isinstance(t, typedesc.ArrayType):
        s, a = storage(t.typ)
        if t.max.lower() == GCCXML_NOSIZE:
            return 0, a
        return s * (int(t.max) - int(t.min) + 1), a
    return int(t.size), int(t.align)

class PackingError(Exception):
    pass

def _calc_packing(struct, fields, pack, isStruct):
    # Try a certain packing, raise PackingError if field offsets,
    # total size ot total alignment is wrong.
    if struct.size is None: # incomplete struct
        return -1
    if struct.name in dont_assert_size:
        return None
    if struct.bases:
        size = struct.bases[0].size
        total_align = struct.bases[0].align
    else:
        size = 0
        total_align = 8 # in bits
    for i, f in enumerate(fields):
        if f.bits: # this code cannot handle bit field sizes.
##            print "##XXX FIXME"
            return -2 # XXX FIXME
        s, a = storage(f.typ)
        if pack is not None:
            a = min(pack, a)
        if size % a:
            size += a - size % a
        if isStruct:
            if size != f.offset:
                raise PackingError, "field %s offset (%s/%s)" % (f.name, size, f.offset)
            size += s
        else:
            size = max(size, s)
        total_align = max(total_align, a)
    if total_align != struct.align:
        raise PackingError, "total alignment (%s/%s)" % (total_align, struct.align)
    a = total_align
    if pack is not None:
        a = min(pack, a)
    if size % a:
        size += a - size % a
    if size != struct.size:
        raise PackingError, "total size (%s/%s)" % (size, struct.size)

def calc_packing(struct, fields):
    # try several packings, starting with unspecified packing
    isStruct = isinstance(struct, typedesc.Structure)
    for pack in [None, 16*8, 8*8, 4*8, 2*8, 1*8]:
        try:
            _calc_packing(struct, fields, pack, isStruct)
        except PackingError, details:
            continue
        else:
            if pack is None:
                return None
            return pack/8
    raise PackingError, "PACKING FAILED: %s" % details

def get_real_type(tp):
    if type(tp) is typedesc.Typedef:
        return get_real_type(tp.typ)
    elif isinstance(tp, typedesc.CvQualifiedType):
        return get_real_type(tp.typ)
    return tp

# XXX These should be filtered out in gccxmlparser.
dont_assert_size = set(
    [
    "__si_class_type_info_pseudo",
    "__class_type_info_pseudo",
    ]
    )

################################################################

class Initializer(object):

    def __call__(self, tp, init, is_pointer=False):
        try:
            mth = getattr(self, tp.__class__.__name__)
        except AttributeError:
            raise TypeError("Cannot initialize %s" % tp.__class__.__name__)
        return mth(tp, init, is_pointer)

    def FundamentalType(self, tp, init, is_pointer=False):
        try:
            mth = getattr(self, ctypes_names[tp.name].replace("None", "void"))
        except AttributeError:
            raise TypeError("Cannot initialize %s" % tp.name)
        return mth(tp, init, is_pointer)

    def CvQualifiedType(self, tp, init, is_pointer=False):
        return self(tp.typ, init, is_pointer)

    def PointerType(self, tp, init, is_pointer=False):
        return self(tp.typ, init, is_pointer=True)

    ##### ctypes types initializers #####

    def void(self, tp, init, is_pointer=False):
        if not is_pointer:
            raise RuntimeError # a void type does not exist
        if init.find('"') >= 0:
            # strip off type casts, if any
            init = init[init.find('"'):]
        value = eval(init)
        return ctypes.c_void_p(value).value

    def c_ubyte(self, tp, init, is_pointer=False):
        value = eval(init)
        return ctypes.c_ubyte(value).value

    def c_char(self, tp, init, is_pointer=False):
        if init.find('"') >= 0:
            init = init[init.find('"'):]
        value = eval(init)
        if isinstance(value, (int, long)):
            if is_pointer:
                return ctypes.c_void_p(value).value
            else:
                return chr(value)
        if not is_pointer:
            assert isinstance(value, basestring)
            assert len(value) == 1
        return value

    def c_wchar(self, tp, init, is_pointer=False):
        if init.find('"') >= 0:
            init = init[init.find('"'):]
        value = eval(init)
        if isinstance(value, (int, long)):
            if is_pointer:
                return ctypes.c_void_p(value).value
            else:
                return unichr(value)
        if not is_pointer:
            assert isinstance(value, basestring)
            assert len(value) == 1
        if isinstance(value, str):
            # gccxml returns unicode initializers as 32-but values in
            # byte strings, with a 3-nul bytes termination:
            # "A\x00\x00\x00B\x00\x00\x00C\x00\x00\x00\x00\x00\x00" -> u"ABC"
            ws = ctypes.sizeof(ctypes.c_wchar)
            if ws == 4:
                v = value[:-3]
                value = "".join(map(unichr, struct.unpack("I" * (len(v)/4), v)))
            elif ws == 2:
                v = value[:-1]
                value = "".join(map(unichr, struct.unpack("H" * (len(v)/2), v)))
        return value

##    def void(self, tp, init, is_pointer=False):
##        if is_pointer:
##            value = eval(value)
##            return ctypes.c_void_p(value).value
##        raise RuntimeError("void???")

    def _init_integer(self, ctyp, suffixes, init):
        value = init.rstrip(suffixes)
        value = eval(value)
        return ctyp(value).value

    def _init_float(self, ctyp, suffixes, init):
        value = init.rstrip(suffixes)
        value = eval(value)
        return ctyp(value).value

    def c_short(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_short, "i", init)
                                                                                            
    def c_ushort(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_ushort, "ui", init)
                                                                                            
    def c_int(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_int, "i", init)
                                                                                            
    def c_uint(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_uint, "ui", init)
                                                                                            
    def c_long(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_long, "l", init)
                                                                                            
    def c_ulong(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_ulong, "ul", init)
                                                                                            
    def c_longlong(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_longlong, "l", init)
                                                                                            
    def c_ulonglong(self, tp, init, is_pointer=False):
        return self._init_integer(ctypes.c_ulonglong, "ul", init)
                                                                                            
    def c_double(self, tp, init, is_pointer=False):
        return self._init_float(ctypes.c_double, "", init)

    def c_float(self, tp, init, is_pointer=False):
        return self._init_float(ctypes.c_float, "f", init)

class Generator(object):
    def __init__(self, output,
                 generate_comments=False,
                 known_symbols=None,
                 searched_dlls=None,
                 preloaded_dlls=[],
                 generate_docstrings=False):
        self.variables = []
        self.output = output
        self.stream = StringIO.StringIO()
        self.imports = StringIO.StringIO()
##        self.stream = self.imports = self.output
        self.generate_comments = generate_comments
        self.generate_docstrings = generate_docstrings
        self.known_symbols = known_symbols or {}
        self.preloaded_dlls = preloaded_dlls
        if searched_dlls is None:
            self.searched_dlls = []
        else:
            self.searched_dlls = searched_dlls

        self.done = set() # type descriptions that have been generated
        self.names = set() # names that have been generated
        self.initialize = Initializer()

    def type_name(self, t, generate=True):
        # Return a string containing an expression that can be used to
        # refer to the type. Assumes the 'from ctypes import *'
        # namespace is available.
        if isinstance(t, typedesc.Typedef):
            return t.name
        if isinstance(t, typedesc.PointerType):
            if ASSUME_STRINGS:
                x = get_real_type(t.typ)
                if isinstance(x, typedesc.FundamentalType):
                    if x.name == "char":
                        self.need_STRING()
                        return "STRING"
                    elif x.name == "wchar_t":
                        self.need_WSTRING()
                        return "WSTRING"

            result = "POINTER(%s)" % self.type_name(t.typ, generate)
            # XXX Better to inspect t.typ!
            if result.startswith("POINTER(WINFUNCTYPE"):
                return result[len("POINTER("):-1]
            if result.startswith("POINTER(CFUNCTYPE"):
                return result[len("POINTER("):-1]
            elif result == "POINTER(None)":
                return "c_void_p"
            return result
        elif isinstance(t, typedesc.ArrayType):
            if t.max.lower() == GCCXML_NOSIZE or t.max == "":
                return "%s * 0" % (self.type_name(t.typ, generate),)
            return "%s * %s" % (self.type_name(t.typ, generate), int(t.max)+1)
        elif isinstance(t, typedesc.FunctionType):
            args = [self.type_name(x, generate) for x in [t.returns] + list(t.iterArgTypes())]
            if "__stdcall__" in t.attributes:
                return "WINFUNCTYPE(%s)" % ", ".join(args)
            else:
                return "CFUNCTYPE(%s)" % ", ".join(args)
        elif isinstance(t, typedesc.CvQualifiedType):
            # const and volatile are ignored
            return "%s" % self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.FundamentalType):
            return ctypes_names[t.name]
        elif isinstance(t, typedesc.Structure):
            return t.name
        elif isinstance(t, typedesc.Enumeration):
            if t.name:
                return t.name
            return "c_int" # enums are integers
        elif isinstance(t, typedesc.Typedef):
            return t.name
        return t.name

    ################################################################

    def Alias(self, alias):
        if alias.typ is not None: # we can resolve it
            self.generate(alias.typ)
            if alias.alias in self.names:
                print >> self.stream, "%s = %s # alias" % (alias.name, alias.alias)
                self.names.add(alias.name)
                return
        # we cannot resolve it
        print >> self.stream, "# %s = %s # alias" % (alias.name, alias.alias)
        print "# unresolved alias: %s = %s" % (alias.name, alias.alias)
            

    def Macro(self, macro):
        # We don't know if we can generate valid, error free Python
        # code. All we can do is to try to compile the code.  If the
        # compile fails, we know it cannot work, so we comment out the
        # generated code; the user may be able to fix it manually.
        #
        # If the compilation succeeds, it may still fail at runtime
        # when the macro is called.
        code = "def %s%s: return %s # macro" % (macro.name, macro.args, macro.body)
        try:
            compile(code, "<string>", "exec")
        except SyntaxError:
            print >> self.stream, "#", code
        else:
            print >> self.stream, code
            self.names.add(macro.name)

    def StructureHead(self, head):
        for struct in head.struct.bases:
            self.generate(struct.get_head())
            self.more.add(struct)
        if self.generate_comments and head.struct.location:
            print >> self.stream, "# %s %s" % head.struct.location
        basenames = [self.type_name(b) for b in head.struct.bases]
        if basenames:
###            method_names = [m.name for m in head.struct.members if type(m) is typedesc.Method]
            print >> self.stream, "class %s(%s):" % (head.struct.name, ", ".join(basenames))
        else:
###            methods = [m for m in head.struct.members if type(m) is typedesc.Method]
            if type(head.struct) == typedesc.Structure:
                print >> self.stream, "class %s(Structure):" % head.struct.name
            elif type(head.struct) == typedesc.Union:
                print >> self.stream, "class %s(Union):" % head.struct.name
        print >> self.stream, "    pass"
        self.names.add(head.struct.name)

    _structures = 0
    def Structure(self, struct):
        self._structures += 1
        self.generate(struct.get_head())
        self.generate(struct.get_body())

    Union = Structure
        
    _typedefs = 0
    def Typedef(self, tp):
        sized_types = {
            "uint8_t":  "c_uint8",
            "uint16_t": "c_uint16",
            "uint32_t": "c_uint32",
            "uint64_t": "c_uint64",
            "int8_t":  "c_int8",
            "int16_t": "c_int16",
            "int32_t": "c_int32",
            "int64_t": "c_int64",
            }
        self._typedefs += 1
        if type(tp.typ) == typedesc.FundamentalType \
           and tp.name in sized_types:
            print >> self.stream, "%s = %s" % \
                  (tp.name, sized_types[tp.name])
            self.names.add(tp.name)
            return
        if type(tp.typ) in (typedesc.Structure, typedesc.Union):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        else:
            self.generate(tp.typ)
        if 0 and self.type_name(tp.typ) in self.known_symbols:
            stream = self.imports
        else:
            stream = self.stream
        if tp.name != self.type_name(tp.typ):
            print >> stream, "%s = %s" % \
                  (tp.name, self.type_name(tp.typ))
        self.names.add(tp.name)

    _arraytypes = 0
    def ArrayType(self, tp):
        self._arraytypes += 1
        self.generate(get_real_type(tp.typ))
        self.generate(tp.typ)

    _functiontypes = 0
    def FunctionType(self, tp):
        self._functiontypes += 1
        self.generate(tp.returns)
        self.generate_all(tp.iterArgTypes())
        
    _pointertypes = 0
    def PointerType(self, tp):
        self._pointertypes += 1
        if type(tp.typ) is typedesc.PointerType:
            self.generate(tp.typ)
        elif type(tp.typ) in (typedesc.Union, typedesc.Structure):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        elif type(tp.typ) is typedesc.Typedef:
            self.generate(tp.typ)
        else:
            self.generate(tp.typ)

    def CvQualifiedType(self, tp):
        self.generate(tp.typ)

    _variables = 0
    _notfound_variables = 0
    def Variable(self, tp):
        self._variables += 1
        dllname = self.find_dllname(tp)

        # avoid conflict varialbe names
        name = tp.name
        if name in self.names:
            if tp.typ not in ctypes_names:
                name += 'obj'
            n = 1
            while name in self.names:
                name = "%s%d" % (name, n)

        if dllname:
            # not enough, we could have:
            #    type2 = type1
            #    var = (type2)obj
            # if type1._fields_ is defined after var,
            # we will in trouble.
            self.generate(tp.typ)
            # calling convention does not matter for in_dll...
            libname = self.get_sharedlib(dllname, "cdecl")
            print >> self.stream, \
                  "%s = (%s).in_dll(%s, '%s')" % (name,
                                                  self.type_name(tp.typ),
                                                  libname,
                                                  tp.name)
            self.names.add(name)
            # wtypes.h contains IID_IProcessInitControl, for example
            return

        # Hm.  The variable MAY be a #define'd symbol that we have
        # artifically created, or it may be an exported variable that
        # is not in the libraries that we search.  Anyway, if it has
        # no tp.init value we can't generate code for it anyway, so we
        # drop it.
        if tp.init is None:
            self._notfound_variables += 1
            return
        try:
            value = self.initialize(tp.typ, tp.init)
        except (TypeError, ValueError, SyntaxError, NameError), detail:
            print "Could not init", (tp.name, tp.init), detail
##            raise
            return
        print >> self.stream, \
              "%s = %r # Variable %s %r" % (name,
                                         value,
                                         self.type_name(tp.typ, False),
                                         tp.init)
        self.names.add(name)

    _enumvalues = 0
    def EnumValue(self, tp):
        value = int(tp.value)
        print >> self.stream, \
              "%s = %d" % (tp.name, value)
        self.names.add(tp.name)
        self._enumvalues += 1

    _enumtypes = 0
    def Enumeration(self, tp):
        self._enumtypes += 1
        print >> self.stream
        if tp.name:
            print >> self.stream, "# values for enumeration '%s'" % tp.name
        else:
            print >> self.stream, "# values for unnamed enumeration"
        # Some enumerations have the same name for the enum type
        # and an enum value.  Excel's XlDisplayShapes is such an example.
        # Since we don't have separate namespaces for the type and the values,
        # we generate the TYPE last, overwriting the value. XXX
        for item in tp.values:
            self.generate(item)
        if tp.name:
            print >> self.stream, "%s = c_int # enum" % tp.name
            self.names.add(tp.name)


    def StructureBody(self, body):
        fields = []
        methods = []
        for m in body.struct.members:
            if type(m) is typedesc.Field:
                fields.append(m)
                if type(m.typ) is typedesc.Typedef:
                    self.generate(get_real_type(m.typ))
                self.generate(m.typ)
            elif type(m) is typedesc.Method:
                methods.append(m)
                self.generate(m.returns)
                self.generate_all(m.iterArgTypes())
            elif type(m) is typedesc.Ignored:
                pass

        if methods:
            # XXX we have parsed the COM interface methods but should
            # we emit any code for them?
            pass
        else:
            # we don't need _pack_ on Unions (I hope, at least), and not
            # on COM interfaces.
            try:
                # gccxml reports a non-zero size on structures that
                # have no fields.  The packing would fail, but it is
                # unneeded anyway so we skip it.
                if fields:
                    pack = calc_packing(body.struct, fields)
                    if pack is not None:
                        print >> self.stream, "%s._pack_ = %s" % (body.struct.name, pack)
            except PackingError, details:
                # if packing fails, write a warning comment to the output.
                import warnings
                message = "Structure %s: %s" % (body.struct.name, details)
                warnings.warn(message, UserWarning)

        if body.struct.bases:
            assert len(body.struct.bases) == 1
            self.generate(body.struct.bases[0].get_body())
        # field definition normally span several lines.
        # Before we generate them, we need to 'import' everything they need.
        # So, call type_name for each field once,
        for f in fields:
            self.type_name(f.typ)

        # unnamed fields get autogenerated names "_0", "_1", "_2", "_3", ...
        unnamed_fields = {}
        for f in fields:
            # _anonymous_ fields are fields of type Structure or Union,
            # that have no name.
            if not f.name and isinstance(f.typ, (typedesc.Structure, typedesc.Union)):
                unnamed_fields[f] = "_%d" % len(unnamed_fields)
        if unnamed_fields:
            print >> self.stream, "%s._anonymous_ = %r" % \
                  (body.struct.name, unnamed_fields.values())
        if fields:
            print >> self.stream, "%s._fields_ = [" % body.struct.name

            if self.generate_comments and body.struct.location:
                print >> self.stream, "    # %s %s" % body.struct.location
            index = 0
            for f in fields:
                fieldname = unnamed_fields.get(f, f.name)
                if f.bits is None:
                    print >> self.stream, "    ('%s', %s)," % \
                       (fieldname, self.type_name(f.typ))
                else:
                    print >> self.stream, "    ('%s', %s, %s)," % \
                          (fieldname, self.type_name(f.typ), f.bits)
            print >> self.stream, "]"
        # disable size checks because they are not portable across
        # platforms:
##        # generate assert statements for size and alignment
##        if body.struct.size and body.struct.name not in dont_assert_size:
##            size = body.struct.size // 8
##            print >> self.stream, "assert sizeof(%s) == %s, sizeof(%s)" % \
##                  (body.struct.name, size, body.struct.name)
##            align = body.struct.align // 8
##            print >> self.stream, "assert alignment(%s) == %s, alignment(%s)" % \
##                  (body.struct.name, align, body.struct.name)

    def find_dllname(self, func):
        if hasattr(func, "dllname"):
            return func.dllname
        name = func.name
        for dll in self.searched_dlls:
            try:
                getattr(dll, name)
            except AttributeError:
                pass
            else:
                return dll._name
##        if self.verbose:
        # warnings.warn, maybe?
##        print >> sys.stderr, "function %s not found in any dll" % name
        return None

    _c_libraries = None
    def need_CLibraries(self):
        # Create a '_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._c_libraries is None:
            self._c_libraries = {}
            print >> self.imports, "_libraries = {}"

    _stdcall_libraries = None
    def need_WinLibraries(self):
        # Create a '_stdcall_libraries' doctionary in the generated code, if
        # it not yet exists. Will map library pathnames to loaded libs.
        if self._stdcall_libraries is None:
            self._stdcall_libraries = {}
            print >> self.imports, "_stdcall_libraries = {}"

    def get_sharedlib(self, dllname, cc):
        if cc == "stdcall":
            self.need_WinLibraries()
            if not dllname in self._stdcall_libraries:
                print >> self.imports, "_stdcall_libraries[%r] = WinDLL(%r)" % (dllname, dllname)
                self._stdcall_libraries[dllname] = None
            return "_stdcall_libraries[%r]" % dllname
        self.need_CLibraries()
        if self.preloaded_dlls != []:
          global_flag = ", mode=RTLD_GLOBAL"
        else:
          global_flag = ""
        if not dllname in self._c_libraries:
            print >> self.imports, "_libraries[%r] = CDLL(%r%s)" % (dllname, dllname, global_flag)
            self._c_libraries[dllname] = None
        return "_libraries[%r]" % dllname

    _STRING_defined = False
    def need_STRING(self):
        if self._STRING_defined:
            return
        print >> self.imports, "STRING = c_char_p"
        self._STRING_defined = True

    _WSTRING_defined = False
    def need_WSTRING(self):
        if self._WSTRING_defined:
            return
        print >> self.imports, "WSTRING = c_wchar_p"
        self._WSTRING_defined = True

    _functiontypes = 0
    _notfound_functiontypes = 0
    def Function(self, func):
        dllname = self.find_dllname(func)
        if dllname:
            self.generate(func.returns)
            self.generate_all(func.iterArgTypes())
            args = [self.type_name(a) for a in func.iterArgTypes()]
            if "__stdcall__" in func.attributes:
                cc = "stdcall"
            else:
                cc = "cdecl"

            libname = self.get_sharedlib(dllname, cc)

            argnames = [a or "p%d" % (i+1) for i, a in enumerate(func.iterArgNames())]

            if self.generate_comments and func.location:
                print >> self.stream, "# %s %s" % func.location
            print >> self.stream, "%s = %s.%s" % (func.name, libname, func.name)
            print >> self.stream, "%s.restype = %s" % (func.name, self.type_name(func.returns))
            if self.generate_comments:
                print >> self.stream, "# %s(%s)" % (func.name, ", ".join(argnames))
            print >> self.stream, "%s.argtypes = [%s]" % (func.name, ", ".join(args))
            
            if self.generate_docstrings:
                def typeString(typ):
                    if hasattr(typ, 'name'):
                        return typ.name
                    elif hasattr(typ, 'typ') and type(typ) == typedesc.PointerType:
                        return typeString(typ.typ) + " *"
                    else:
                        return "unknown"
                argsAndTypes = zip([typeString(t) for t in func.iterArgTypes()], argnames)
                print >> self.stream, """%(funcname)s.__doc__ = \\
\"\"\"%(ret)s %(funcname)s(%(args)s)
%(file)s:%(line)s\"\"\"""" % \
                    {'funcname': func.name, 
                    'args': ", ".join(["%s %s" % i for i in argsAndTypes]),
                    'file': func.location[0],
                    'line': func.location[1],
                    'ret': typeString(func.returns),
                    }

            self.names.add(func.name)
            self._functiontypes += 1
        else:
            self._notfound_functiontypes += 1

    def FundamentalType(self, item):
        pass # we should check if this is known somewhere
##        name = ctypes_names[item.name]
##        if name !=  "None":
##            print >> self.stream, "from ctypes import %s" % name
##        self.done.add(item)

    ########

    def generate(self, item, do_variable=False):
        if item in self.done:
            return
        if isinstance(item, typedesc.StructureHead):
            name = getattr(item.struct, "name", None)
        else:
            name = getattr(item, "name", None)
        if name in self.known_symbols:
            mod = self.known_symbols[name]
            print >> self.imports, "from %s import %s" % (mod, name)
            self.done.add(item)
            if isinstance(item, typedesc.Structure):
                self.done.add(item.get_head())
                self.done.add(item.get_body())
            return

        # We have to put variable in the end to avoid instantiate
        # structure before define it _fields_
        if not do_variable and isinstance(item, typedesc.Variable):
            self.variables.append(item)
            # have to add it to done in order to stop generate_items()
            self.done.add(item)
        else:
            mth = getattr(self, type(item).__name__)
            # to avoid infinite recursion, we have to mark it as done
            # before actually generating the code.
            self.done.add(item)
            mth(item)

    def generate_all(self, items):
        for item in items:
            self.generate(item)

    def cmpitems(a, b):
	a = getattr(a, "location", None)
	b = getattr(b, "location", None)
	if a is None: return -1
	if b is None: return 1
	return cmp(a[0],b[0]) or cmp(int(a[1]),int(b[1]))
    cmpitems = staticmethod(cmpitems)

    def generate_items(self, items):
        items = set(items)
        loops = 0
        while items:
            loops += 1
            self.more = set()
            self.generate_all(sorted(items, self.cmpitems))

            items |= self.more
            items -= self.done

        # Do variables
        # fool generate() first
        done = self.done
        self.done = set()
        # Avoid recursive type defined in variables, push out 
        # types before we generate variables
        for item in self.variables:
            dllname = self.find_dllname(item)
            if dllname:
                self.generate(item.typ)

        while self.variables:
            variables = self.variables
            self.variables = []
            for item in variables:
                self.generate(item, do_variable=True)
        self.done.update(done)
        return loops

    def generate_code(self, items):
        print >> self.imports, "from ctypes import *"
        print >> self.imports, "\n".join(["CDLL('%s', RTLD_GLOBAL)" % preloaded_dll
                                          for preloaded_dll
                                          in  self.preloaded_dlls])
        loops = self.generate_items(items)

        self.output.write(self.imports.getvalue())
        self.output.write("\n\n")
        self.output.write(self.stream.getvalue())

        text = "__all__ = [%s]" % ", ".join([repr(str(n)) for n in self.names])

        wrapper = textwrap.TextWrapper(break_long_words=False,
                                       subsequent_indent="           ")
        for line in wrapper.wrap(text):
            print >> self.output, line
        return loops

    def print_stats(self, stream):
        total = self._structures + self._functiontypes + self._enumtypes + self._typedefs +\
                self._pointertypes + self._arraytypes
        print >> stream, "###########################"
        print >> stream, "# Symbols defined:"
        print >> stream, "#"
        print >> stream, "# Variables:          %5d" % self._variables
        print >> stream, "# Struct/Unions:      %5d" % self._structures
        print >> stream, "# Functions:          %5d" % self._functiontypes
        print >> stream, "# Enums:              %5d" % self._enumtypes
        print >> stream, "# Enum values:        %5d" % self._enumvalues
        print >> stream, "# Typedefs:           %5d" % self._typedefs
        print >> stream, "# Pointertypes:       %5d" % self._pointertypes
        print >> stream, "# Arraytypes:         %5d" % self._arraytypes
        print >> stream, "# unknown functions:  %5d" % self._notfound_functiontypes
        print >> stream, "# unknown variables:  %5d" % self._notfound_variables
        print >> stream, "#"
        print >> stream, "# Total symbols: %5d" % total
        print >> stream, "###########################"

################################################################

def generate_code(xmlfile,
                  outfile,
                  expressions=None,
                  symbols=None,
                  verbose=False,
                  generate_comments=False,
                  known_symbols=None,
                  searched_dlls=None,
                  types=None,
                  preloaded_dlls=[],
                  generate_docstrings=False,):
    # expressions is a sequence of compiled regular expressions,
    # symbols is a sequence of names
    from gccxmlparser import parse
    items = parse(xmlfile)

    # filter symbols to generate
    todo = []

    if types:
        items = [i for i in items if isinstance(i, types)]
    
    if symbols:
        syms = set(symbols)
        for i in items:
            if i.name in syms:
                todo.append(i)
                syms.remove(i.name)

        if syms:
            print "symbols not found", list(syms)

    if expressions:
        for i in items:
            for s in expressions:
                if i.name is None:
                    continue
                match = s.match(i.name)
                # we only want complete matches
                if match and match.group() == i.name:
                    todo.append(i)
                    break
    if symbols or expressions:
        items = todo

    ################
    gen = Generator(outfile,
                    generate_comments=generate_comments,
                    generate_docstrings=generate_docstrings,
                    known_symbols=known_symbols,
                    searched_dlls=searched_dlls,
                    preloaded_dlls=preloaded_dlls)

    loops = gen.generate_code(items)
    if verbose:
        gen.print_stats(sys.stderr)
        print >> sys.stderr, "needed %d loop(s)" % loops

