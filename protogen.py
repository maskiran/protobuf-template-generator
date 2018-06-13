import gflags
import google.protobuf
import os
import sys


FLAGS = gflags.FLAGS


PARENT_OBJECTS = []
CODE = []


def _make_var_name(obj):
    """
    Create a variable name for an object. Uses the class the name and lowercase it
    """
    return obj.__class__.__name__.lower()


def _set_field_values(obj, code_var_name):
    """
    Set the default values for all the variables in the object
    """
    for fname, field in obj.DESCRIPTOR.fields_by_name.items():
        if isinstance(getattr(obj, fname), (str, unicode)):
            setattr(obj, fname, "tmp")
            CODE.append("%s.%s = 'tmp'" % (code_var_name, fname))
        elif isinstance(getattr(obj, fname), (int, long, float)):
            setattr(obj, fname, 1)
            CODE.append("%s.%s = 1" % (code_var_name, fname))
        elif isinstance(getattr(obj, fname), bool):
            setattr(obj, fname, True)
            CODE.append("%s.%s = True" % (code_var_name, fname))
        elif isinstance(getattr(obj, fname), google.protobuf.internal.containers.RepeatedScalarFieldContainer):
            # i dont know if the internal element is list or string, so
            # try to set one type and if i get exception try to set the
            # other one
            try:
                getattr(obj, fname).extend(['tmp'])
                CODE.append("%s.%s.extend(['tmp'])" % (code_var_name, fname))
            except:
                getattr(obj, fname).extend([1])
                CODE.append("%s.%s.extend([1])" % (code_var_name, fname))
        elif isinstance(getattr(obj, fname), google.protobuf.internal.containers.RepeatedCompositeFieldContainer):
            PARENT_OBJECTS.append(type(obj))
            # set the values of the list item by adding a new item
            new_obj = getattr(obj, fname).add()
            CODE.append("%s = %s.%s.add()" %
                        (_make_var_name(new_obj), code_var_name, fname))
            # if the type(new_obj) exists in PARENT_OBJECTS, its a
            # recursion and cannot create template for that
            if type(new_obj) not in PARENT_OBJECTS:
                _set_field_values(new_obj, _make_var_name(new_obj))
        else:
            # fname is another proto message
            # can set the attributes of the proto
            # message directly without a need to create the object
            # using the dotsyntax of the object
            PARENT_OBJECTS.append(type(obj))
            new_obj = getattr(obj, fname)
            # if the type(new_obj) exists in PARENT_OBJECTS, its a
            # recursion and cannot create template for that
            if type(new_obj) not in PARENT_OBJECTS:
                tmp_var = "%s.%s" % (code_var_name, fname)
                _set_field_values(new_obj, tmp_var)

    if PARENT_OBJECTS:
        PARENT_OBJECTS.pop()
    return


def _import_module(module_name):
    """
    Import the given module and return it.
    """
    # this script could be launched from anywhere. so add the current
    # dir to sys.path.
    # if the module name is given as a path, add the dir to sys.path
    add_dirs = []
    dir_name = os.path.dirname(os.path.abspath(module_name))
    add_dirs.append(dir_name)
    add_dirs.append(os.getcwd())
    for dir_name in add_dirs:
        if dir_name not in sys.path:
            sys.path.insert(0, dir_name)
    __import__(module_name)
    # __import__ returns the top level package only. to get the module
    # name, call the following
    # https://docs.python.org/2.6/library/functions.html#__import__
    proto = sys.modules[module_name]
    return proto


def get_object(module_name, msg_name_str):
    """
    Create the protobuf object in the module_name and the given
    msg_name_str and with all the values filled in for the attributes.
    This is equivalent to:
    obj = module_name.msg_name_str()
    obj.attrname = value
    return obj
    """
    proto = _import_module(module_name)
    obj = getattr(proto, msg_name_str)()
    CODE.append("%s = %s()" % (_make_var_name(obj), msg_name_str))
    _set_field_values(obj, _make_var_name(obj))
    return obj


def get_code(module_name, msg_name_str):
    """
    Get the python code to create the protobuf message msg_name_str
    in the given module_name.
    This code can then be used in a python script, to customize it
    further. The text that would be returned is as follows:
    obj = msg_name_str()
    obj.attrname = value1
    """
    get_object(module_name, msg_name_str)
    return "\n".join(CODE)


def list_messages(module_name):
    proto = _import_module(module_name)
    args = []
    members = dir(proto)
    for m in members:
        args.append(m)
    return args


if __name__ == "__main__":
    gflags.DEFINE_string("module",
                         "",
                         "Module Name (e.g insights_interface_pb2\
                            - with or without .py)",
                         short_name='m')
    gflags.DEFINE_bool("list",
                       False,
                       "List all the Arg messages in the module\
                           provided using -m <modname>",
                       short_name='l')
    gflags.DEFINE_string("message",
                         "",
                         "Message Name",
                         short_name='g')
    gflags.DEFINE_bool("text",
                       False,
                       "Generate text template",
                       short_name='t')
    gflags.DEFINE_bool("code",
                       False,
                       "Generate Python code template",
                       short_name='c')
    FLAGS(sys.argv)
    # -m insights_interface_pb2 -g UpdateEntityTypeArg
    module = os.path.basename(FLAGS.module).replace('.py', '')

    if FLAGS.list:
        l = list_messages(module)
        print "\n".join(l)
    else:
        obj = get_object(module, FLAGS.message)
        if FLAGS.text:
            print obj
        if FLAGS.code:
            print "\n".join(CODE)
