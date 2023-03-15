CSV_CODE = 'PLATEAU_3D-Spatial-ID_CSV'
CSV_VERSION = '0100'
CSV_DIRECTORY = 'spatialid'

NAMESPACES = {
    'uro': {
        'uri': 'https://www.geospatial.jp/iur/uro/2.0',
        'location': '../../schemas/iur/uro/2.0/urbanObject.xsd',
    },
    'urf': {
        'uri': 'https://www.geospatial.jp/iur/urf/2.0',
        'location': '../../schemas/iur/urf/2.0/urbanFunction.xsd',
    },
}

SPATIALID_EMBEDDING = 'embedding'
SPATIALID_REFERENCE = 'reference'
SPATIALID_BOTH = 'both'
SPATIALID_LIST = [
    SPATIALID_EMBEDDING,
    SPATIALID_REFERENCE,
    SPATIALID_BOTH,
]
