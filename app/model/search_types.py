from enum import Enum

class SearchType(Enum):
    AUDIO = 'audio'
    ZIP = 'zip'
    DOC = 'doc'
    EXE = 'exe'
    FOLDER = 'folder'
    PIC = 'pic'
    VIDEO = 'video'
    CUSTOM_EXT = 'custom_ext'
    CUSTOM_LOCATION = 'custom_location'