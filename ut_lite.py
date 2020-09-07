import hashlib
import json
import uuid
import six
import pickle
import codecs
import collections
import numpy as np

## from types

PRIMATIVE_TYPES = (
    tuple(six.string_types) + (bytes, list, dict, set, frozenset, int, float,
                               bool, type(None))
)

BooleanType = bool

NUMPY_TYPE_TUPLE = (
    tuple([np.ndarray] + list(set(np.typeDict.values()))))

VALID_BOOL_TYPES = (BooleanType, np.bool_)

def is_str(var):
    return isinstance(var, six.string_types)


def fuzzy_subset(str_):
    """
    converts a string into an argument to list_take
    """
    if str_ is None:
        return str_
    if ':' in str_:
        return smart_cast(str_, slice)
    if str_.startswith('['):
        return smart_cast(str_[1:-1], list)
    else:
        return smart_cast(str_, list)

def bool_from_str(str_):
    lower = str_.lower()
    if lower == 'true':
        return True
    elif lower == 'false':
        return False
    else:
        raise TypeError('string does not represent boolean')

def smart_cast(var, type_):

    if type_ is None or var is None:
        return var
    #if not isinstance(type_, six.string_types):
    try:
        if issubclass(type_, type(None)):
            return var
    except TypeError:
        pass
    if is_str(var):
        if type_ in VALID_BOOL_TYPES:
            return bool_from_str(var)
        elif type_ is slice:
            args = [None if len(arg) == 0 else int(arg) for arg in var.split(':')]
            return slice(*args)
        elif type_ is list:
            # need more intelligent parsing here
            subvar_list = var.split(',')
            return [smart_cast2(subvar) for subvar in subvar_list]
        elif isinstance(type_, six.string_types):
            if type_ == 'fuzzy_subset':
                return fuzzy_subset(var)
            if type_ == 'eval':
                return eval(var, {}, {})
            #elif type_ == 'fuzzy_int':
            #    return fuzzy_subset(var)
            else:
                raise NotImplementedError('Uknown smart type_=%r' % (type_,))
    return type_(var)

def try_cast(var, type_, default=None):
    if type_ is None:
        return var
    try:
        return smart_cast(var, type_)
    except Exception:
        return default

def smart_cast2(var):
    if var is None:
        return None
    if isinstance(var, six.string_types):
        castvar = None
        lower = var.lower()
        if lower == 'true':
            return True
        elif lower == 'false':
            return False
        elif lower == 'none':
            return None
        if var.startswith('[') and var.endswith(']'):
            #import re
            #subvar_list = re.split(r',\s*' + ut.negative_lookahead(r'[^\[\]]*\]'), var[1:-1])
            return smart_cast(var[1:-1], list)
        elif var.startswith('(') and var.endswith(')'):
            #import re
            #subvar_list = re.split(r',\s*' + ut.negative_lookahead(r'[^\[\]]*\]'), var[1:-1])
            return tuple(smart_cast(var[1:-1], list))
        type_list = [int, float]
        for type_ in type_list:
            castvar = try_cast(var, type_)
            if castvar is not None:
                break
        if castvar is None:
            castvar = var
    else:
        castvar = var
    return castvar


## from cache
def to_json(val, allow_pickle=False, pretty=False):
    UtoolJSONEncoder = make_utool_json_encoder(allow_pickle)
    json_kw = {}
    json_kw['cls'] = UtoolJSONEncoder
    if pretty:
        json_kw['indent'] = 4
        json_kw['separators'] = (',', ': ')
    json_str = json.dumps(val, **json_kw)
    return json_str


def from_json(json_str, allow_pickle=False):
    if six.PY3:
        if isinstance(json_str, bytes):
            json_str = json_str.decode('utf-8')
    UtoolJSONEncoder = make_utool_json_encoder(allow_pickle)
    object_hook = UtoolJSONEncoder._json_object_hook
    val = json.loads(json_str, object_hook=object_hook)
    return val


def make_utool_json_encoder(allow_pickle=False):

    PYOBJECT_TAG = '__PYTHON_OBJECT__'
    UUID_TAG = '__UUID__'
    SLICE_TAG = '__SLICE__'

    def decode_pickle(text):
        obj = pickle.loads(codecs.decode(text.encode(), 'base64'))
        return obj

    def encode_pickle(obj):
        try:
            # Use protocol 2 to support both python2.7 and python3
            COMPATIBLE_PROTOCOL = 2
            pickle_bytes = pickle.dumps(obj, protocol=COMPATIBLE_PROTOCOL)
        except Exception:
            raise
        text = codecs.encode(pickle_bytes, 'base64').decode()
        return text

    type_to_tag = collections.OrderedDict([
        (slice, SLICE_TAG),
        (uuid.UUID, UUID_TAG),
        (object, PYOBJECT_TAG),
    ])

    tag_to_type = {tag: type_ for type_, tag in type_to_tag.items()}

    def slice_part(c):
        return '' if c is None else str(c)

    def encode_slice(s):
        parts = [slice_part(s.start), slice_part(s.stop), slice_part(s.step)]
        return ':'.join(parts)

    def decode_slice(x):
        return smart_cast(x, slice)

    encoders = {
        UUID_TAG: str,
        SLICE_TAG: encode_slice,
        PYOBJECT_TAG: encode_pickle,
    }

    decoders = {
        UUID_TAG: uuid.UUID,
        SLICE_TAG: decode_slice,
        PYOBJECT_TAG: decode_pickle,
    }

    if not allow_pickle:
        del encoders[PYOBJECT_TAG]
        del decoders[PYOBJECT_TAG]
        type_ = tag_to_type[PYOBJECT_TAG]
        del tag_to_type[PYOBJECT_TAG]
        del type_to_tag[type_]

    class UtoolJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, NUMPY_TYPE_TUPLE):
                return obj.tolist()
            elif six.PY3 and isinstance(obj, bytes):
                return obj.decode('utf-8')
            elif isinstance(obj, (set, frozenset)):
                return list(obj)
                # return json.JSONEncoder.default(self, list(obj))
                # return [json.JSONEncoder.default(o) for o in obj]
            elif isinstance(obj, PRIMATIVE_TYPES):
                return json.JSONEncoder.default(self, obj)
            elif  hasattr(obj, '__getstate__') and not isinstance(obj, uuid.UUID):
                return obj.__getstate__()
            else:
                for type_, tag in type_to_tag.items():
                    if isinstance(obj, type_):
                        #print('----')
                        #print('encoder obj = %r' % (obj,))
                        #print('encoder type_ = %r' % (type_,))
                        func = encoders[tag]
                        text = func(obj)
                        return {tag: text}
                raise TypeError('Invalid serialization type=%r' % (type(obj)))

        @classmethod
        def _json_object_hook(cls, value, verbose=False, **kwargs):
            if len(value) == 1:
                tag, text = list(value.items())[0]
                if tag in decoders:
                    #print('----')
                    #print('decoder tag = %r' % (tag,))
                    func = decoders[tag]
                    obj = func(text)
                    #print('decoder obj = %r' % (obj,))
                    return obj
            else:
                return value
            return value
    return UtoolJSONEncoder

## from hash
if six.PY3:
    def _ensure_hashable_bytes(hashable_):
        # If hashable_ is text (python3)
        if isinstance(hashable_, bytes):
            return hashable_
        elif isinstance(hashable_, str):
            return hashable_.encode('utf-8')
        elif isinstance(hashable_, int):
            return hashable_.to_bytes(4, byteorder='big')
            # return int_.to_bytes(8, byteorder='big')  # TODO: uncomment
        elif isinstance(hashable_, (list, tuple)):
            return str(hashable_).encode('utf-8')
        else:
            return hashable_
elif six.PY2:
    import struct
    def _ensure_hashable_bytes(hashable_):
        # If hashable_ is data (python2)
        if isinstance(hashable_, bytes):
            return hashable_
        elif isinstance(hashable_, str):
            return hashable_.encode('utf-8')
        elif isinstance(hashable_, int):
            return struct.pack('>i', hashable_)
        elif isinstance(hashable_, (list, tuple)):
            return str(hashable_).encode('utf-8')
        else:
            return bytes(hashable_)


def augment_uuid(uuid_, *hashables):
    #from six.moves import reprlib
    #uuidhex_data   = uuid_.get_bytes()
    uuidhex_data   = uuid_.bytes
    #hashable_str    = ''.join(map(repr, hashables))
    # Python 2 and 3 diverge here because repr returns
    # ascii data in python2 and unicode text in python3
    # it would be nice to
    # warnings.warn('[ut] should not use repr when hashing', RuntimeWarning)
    def tmprepr(x):
        y = repr(x)
        # hack to remove u prefix
        if isinstance(x, six.string_types):
            if y.startswith('u'):
                y = y[1:]
        return y
    if six.PY2:
        hashable_text = ''.join(map(tmprepr, hashables))
        hashable_data = hashable_text.encode('utf-8')
        #hashable_data = b''.join(map(bytes, hashables))
    elif six.PY3:
        hashable_text    = ''.join(map(tmprepr, hashables))
        hashable_data = hashable_text.encode('utf-8')
        #hashable_data = b''.join(map(bytes, hashables))
    augmented_data   = uuidhex_data + hashable_data
    augmented_uuid_ = hashable_to_uuid(augmented_data)
    return augmented_uuid_



def hashable_to_uuid(hashable_):

    bytes_ = _ensure_hashable_bytes(hashable_)
    try:
        bytes_sha1 = hashlib.sha1(bytes_)
    except TypeError:
        print('hashable_ = %r' % (hashable_,))
        print('bytes_ = %r' % (bytes_,))
        raise
    # Digest them into a hash
    hashbytes_20 = bytes_sha1.digest()
    hashbytes_16 = hashbytes_20[0:16]
    uuid_ = uuid.UUID(bytes=hashbytes_16)
    return uuid_

def get_file_uuid(fpath, hasher=None, stride=1):
    """ Creates a uuid from the hash of a file
    """
    if hasher is None:
        hasher = hashlib.sha1()  # 20 bytes of output
        #hasher = hashlib.sha256()  # 32 bytes of output
    # sha1 produces a 20 byte hash
    hashbytes_20 = get_file_hash(fpath, hasher=hasher, stride=stride)
    # sha1 produces 20 bytes, but UUID requires 16 bytes
    hashbytes_16 = hashbytes_20[0:16]
    uuid_ = uuid.UUID(bytes=hashbytes_16)
    return uuid_




def get_file_hash(fpath, blocksize=65536, hasher=None, stride=1,
                  hexdigest=False):
    if hasher is None:
        hasher = hashlib.sha1()
    with open(fpath, 'rb') as file_:
        buf = file_.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            if stride > 1:
                file_.seek(blocksize * (stride - 1), 1)  # skip blocks
            buf = file_.read(blocksize)
        if hexdigest:
            return hasher.hexdigest()
        else:
            return hasher.digest()