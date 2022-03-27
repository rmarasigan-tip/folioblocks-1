"""
Literal Constants (constants.py) | A set of variables for references for the components that needs it.

This file is part of FolioBlocks.

FolioBlocks is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
FolioBlocks is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with FolioBlocks. If not, see <https://www.gnu.org/licenses/>.
"""

from enum import Enum, IntEnum, auto
from pathlib import Path
from typing import Any, Callable, Final
from typing import NewType as _N
from typing import TypeVar, Union

from asgiref.typing import ASGIApplication


# ! Priority Classification Types
class DocToRequestTypes(IntEnum):
    # TODO: We need more information. Preferrable under
    TOR = auto()
    SPECIFIED = auto()


# # Custom Variable Types
NotificationContext = list[dict[str, Any]]
RoleContext = dict[str, Any]
DocumentSet = list[dict[str, Any]]
RequestPayloadContext = dict[str, Any]

# # Custom Assertable Types
# TODO: DocumentSet is unconfirmed because I don't have proper vision of what would be the output.
AcademicExperience = _N("AcademicExperience", str)
AddressUUID = _N("AddressUUID", str)
ArgumentParameter = _N("ArgumentParameter", str)
ArgumentDescription = _N("ArgumentDescription", str)
BlockID = _N("BlockID", str)
Certificates = _N("Certificates", DocumentSet)
CredentialContext = _N("CredentialContext", str)
DocRequestType = _N("DocRequestType", DocToRequestTypes)
Documents = _N("Documents", DocumentSet)
DocumentMeta = _N("DocumentMeta", str)
DocumentProof = _N("DocumentProof", DocumentSet)
GenericUUID = _N("GenericUUID", str)
HashUUID = _N("HashUUID", str)
HashedData = _N("HashedData", str)
InternExperience = _N("InternExperience", DocumentSet)
IPAddress = _N("IPAddress", str)
IPPort = _N("IPPort", int)
NodeRole = _N("NodeRole", str)
JWTToken = _N("JWTToken", str)
ProgramMetadata = _N("ProgramMetadata", str)
RawData = _N("RawData", str)
RegExp = _N("RegExp", str)
RuntimeLoopContext = _N("RuntimeLoopContext", str)
RequestContext = _N("RequestContext", str)
URLAddress = _N("URLAddress", str)
UserRole = _N("UserRole", str)
TxID = _N("TxID", str)
WorkExperience = _N("WorkExperience", DocumentSet)
# # Custom Typed Types
# * For the exceptions.
# BlockAttribute = TypeVar("BlockAttribute", int, str, list["Transaction"], None)  # TODO.
Expects = TypeVar("Expects", str, object)
Has = TypeVar("Has", str, object)
# IdentityTokens = TypeVar("IdentityTokens", AddressUUID, JWTToken) # ???
KeyContext = TypeVar("KeyContext", str, bytes, None)
fn = TypeVar(  # ! Doesn't work for now.
    "fn", bound=Callable[..., Any]
)  # https://stackoverflow.com/questions/65621789/mypy-untyped-decorator-makes-function-my-method-untyped

# # Constants, API
QUERY_CURRENT_INDEX_PAGE_NAME: Final[str] = "Current Index Page"
QUERY_CURRENT_INDEX_NAME_DESCRIPTION: Final[
    str
] = "The page you are currently sitting, defaults to page 1. Other pages are available if the `<context>_count` is higher than the number of returned blocks."

QUERY_TRANSACTION_RETURN_NAME: Final[str] = "Number of Transaction Return"
QUERY_TRANSACTION_RETURN_DESCRIPTION: Final[
    str
] = "The number of transactions to return."

# # Constants / Constraints, Auth
BLOCK_HASH_LENGTH: Final[int] = 64
FERNET_KEY_LENGTH: Final[int] = 44
SECRET_KEY_LENGTH: Final[int] = 32
MAX_JWT_HOLD_TOKEN: Final[int] = 5

UUID_KEY_PREFIX: Final[str] = "fl"
UUID_KEY_LENGTH: Final[int] = 35
AUTH_ENV_FILE_NAME: Final[str] = ".env"

AUTH_CODE_MIN_CONTEXT: Final[int] = 4
AUTH_CODE_MAX_CONTEXT: Final[int] = 32

# # Constants, Blockchain
BLOCKCHAIN_HASH_BLOCK_DIFFICULTY: Final[int] = 4
BLOCKCHAIN_REQUIRED_GENESIS_BLOCKS: Final[int] = 15

# # Constants, Auth: JWT
JWT_DAY_EXPIRATION: Final[int] = 7
JWT_ALGORITHM: Final[str] = "HS256"

# # Constants, FastAPI Configs

CORS_ALLOW_CREDENTIALS: Final[bool] = True
CORS_ALLOWED_HEADERS: Final[list[str]] = ["*"]
CORS_ALLOWED_METHODS: Final[list[str]] = ["DELETE", "GET", "POST", "PUT"]
CORS_ALLOWED_ORIGINS: Final[list[str]] = ["*"]

# # Constants, General
ENUM_NAME_PATTERN: RegExp = RegExp(r"[A-Z]")
ASYNC_TARGET_LOOP: Final[str] = "uvicorn"
ASGI_APP_TARGET: Union[ASGIApplication, str] = "__main__:api_handler"

# # Constants, Auth: SMTP Email
DEFAULT_SMTP_URL: Final[str] = "smtp.gmail.com"
DEFAULT_SMTP_PORT: Final[int] = 465
DEFAULT_SMTP_CONNECT_MAX_RETRIES: Final[int] = 10

# # Constants, Resources
DATABASE_NAME: Final[str] = "folioblocks-node.db"
DATABASE_RAW_PATH: str = f"{Path(__file__).cwd()}/{DATABASE_NAME}"
DATABASE_URL_PATH: str = f"sqlite:///{DATABASE_RAW_PATH}"

BLOCKCHAIN_NAME: Final[str] = "folioblocks-chain.json"
BLOCKCHAIN_RAW_PATH: str = f"{Path(__file__).cwd()}/{BLOCKCHAIN_NAME}"

# # Constants, Template Models with Pydantic
# ! These are used when initializing new resources.

BLOCKCHAIN_NODE_JSON_TEMPLATE: dict[str, list[Any]] = {"chain": []}

# # Constraints — Node Operation Parameter
NODE_IP_ADDR: Final[IPAddress] = IPAddress(
    "127.0.0.1"
)  # - The host from where the master node will establish its connection, and the miners will attempt to connect to.
MASTER_NODE_LIMIT_CONNECTED_NODES: Final[
    int
] = 4  # - The number of nodes that should exists in the network. Master node will reject any connections when the pool is full.
MASTER_NODE_IP_PORT: Final[IPPort] = IPPort(
    5000
)  # - Contains the port from where the `MASTER_NODE` will attempt to live. Should be overridable
# # Enums - API Models
class BaseAPI(Enum):
    ADMIN = "Admin API"
    DASHBOARD = "Dashboard API"
    ENTITY = "Entity API"
    EXPLORER = "Explorer API"
    NODE = "Node API"

    """
    Note that, we only need to govern the user for becoming as a Node User or as an organization representative.
    """


class AdminAPI(Enum):
    REQUEST_TO_ACCESS = f"{BaseAPI.ADMIN.value}: Access Generators"
    # REQUEST_AS_ORG = ""


class DashboardAPI(Enum):
    DASHBOARD_GENERAL_API = f"{BaseAPI.DASHBOARD.value}: General"
    APPLICANT_API = f"{BaseAPI.DASHBOARD.value}: Applicant"
    EMPLOYER_API = f"{BaseAPI.DASHBOARD.value}: Employer"
    INSTITUTION_API = f"{BaseAPI.DASHBOARD.value}: Institution"


class EntityAPI(Enum):
    ENTITY_GENERAL_API = f"{BaseAPI.ENTITY.value}: General"
    LOGIN_API = f"{BaseAPI.ENTITY.value}: Login"
    REGISTRATION_API = f"{BaseAPI.ENTITY.value}: Registration"


class ExplorerAPI(Enum):
    GENERAL_FETCH = f"{BaseAPI.EXPLORER.value}: General Fetch"
    LIST_FETCH = f"{BaseAPI.EXPLORER.value}: List Fetch"
    SPECIFIC_FETCH = f"{BaseAPI.EXPLORER.value}: Specific Fetch"
    BLOCK_FETCH = f"{BaseAPI.EXPLORER.value}: Block Fetch"
    TRANSACTION_FETCH = f"{BaseAPI.EXPLORER.value}: Transaction Fetch"
    ADDRESS_FETCH = f"{BaseAPI.EXPLORER.value}: Address Fetch"


class NodeAPI(Enum):
    GENERAL_NODE_API = f"{BaseAPI.NODE.value}: Overview"
    MASTER_NODE_API = f"{BaseAPI.NODE.value}: Master Node"
    SIDE_NODE_API = f"{BaseAPI.NODE.value}: Side Node"
    NODE_TO_NODE_API = f"{BaseAPI.NODE.value}: Node-to-Node"


# # Enums, Blockchain
class BlockchainIOAction(IntEnum):
    TO_WRITE = auto()
    TO_READ = auto()

    # These are unconfirmed and is subject for removal.
    TO_APPEND = auto()
    TO_OVERWRITE = auto()


# # Enums, Constraints
# ! Blockchain (Explorer) Query
# These are the min and max constraint for querying blockchain data.
class ItemReturnCount(IntEnum):
    LOW = 5
    MIN = 25
    MID = 50
    HIGH = 75
    MAX = 100


# ! Logger Level
class LoggerLevelCoverage(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRACE = "TRACE"


class NodeType(Enum):
    MASTER_NODE = "MASTER_NODE"
    ARCHIVAL_MINER_NODE = "ARCHIVAL_MINER_NODE"


# # Enums, Database
class BlacklistDuration(Enum):  # TODO: These may not be official.
    INDEFINITE = "Indefine."
    WARN_1 = "Warn 1: 1 Day."
    WARN_2 = "Warn 2: 3 Days."
    WARN_3 = "Warn 3: 7 Days."
    FINAL_WARNING = "Final Warning: 2 Weeks."


class GroupType(Enum):
    ORGANIZATION = "Organization Member"
    COMPANY_EMPLOYER = "Company Employer"
    APPLICANTS = "Applicants / Course Graduate"


class TokenStatus(Enum):
    EXPIRED = "Token Expired"
    CREATED_FOR_USE = "Token Recently Created"
    LOGGED_OUT = "Token Disposed: Logged Out"


class UserActivityState(Enum):
    OFFLINE = "Offline"
    ONLINE = "Online"


class UserEntity(Enum):
    NODE_USER = "Node User"
    DASHBOARD_USER = "Dashboard User"
    ADMIN_USER = "Administrator"


# # Enums, Generic
class CryptFileAction(IntEnum):
    TO_DECRYPT = auto()
    TO_ENCRYPT = auto()


# # Enums, HTTP Queues
class HTTPQueueStatus(IntEnum):
    ON_QUEUE = auto()
    UP_NEXT = auto()
    CURRENTLY_WORKING = auto()


class HTTPQueueMethods(IntEnum):
    GET = auto()
    POST = auto()
    PUT = auto()
    PATCH = auto()
    DELETE = auto()


class HTTPQueueResponseFormat(IntEnum):
    AS_OBJECT = auto()
    AS_JSON = auto()
    AS_DICT = auto()


class HTTPQueueTaskType(Enum):
    UNSPECIFIED_HTTP_REQUEST = "HTTP Request"
    UNSPECIFIED = "Unspecified Task"
    INITIATE_CONSENSUS = "Consensus Initialization"
    CHECKPOINT_FILE = "In-Memory to File Checkpoint"
    NEGOTIATION_INITIAL = "Negotiation Phase: Initial"
    NEGOTIATION_PROCESSING = "Negotiation: Processing"
    NEGOTIATION_RECEIVE_RESULT = "Negotiation: End, Receive Result"
    CONSENSUS_MODE = "Consensus Mode, Block Sync"


# # Enums, Transaction models and beyond of a `Block` model.
class StudentActivities(IntEnum):
    AWARDS = auto()
    PROJECTS = auto()
    RECOGNITION = auto()


class StudentStatus(IntEnum):
    ACTIVE = auto()
    INACTIVE = auto()
    TRANSFERRED = auto()


class EmploymentActivityType(IntEnum):
    ACTIVITIES = auto()
    PROJECTS = auto()
    PROMOTION = auto()


class EmploymentStatus(IntEnum):
    ACTIVE = auto()
    TERMINATED = auto()
    RESIGNED = auto()
    INACTIVE = auto()


class TransactionContentCategory(IntEnum):
    EMPLOYMENT = auto()
    SCHOOL = auto()
    ORGANIZATION = auto()


class TransactionContentType(IntEnum):
    pass


class TransactionContentOperation(IntEnum):
    INSERT = auto()
    INVALIDATE = auto()
    UPDATE = auto()


class TransactionStatus(IntEnum):
    SUCCESS = auto()
    FAILED = auto()


# TODO: This will be expanded later on.
class TransactionActions(IntEnum):
    ACCOUNT_GENERATED = auto()
    DOCUMENT_INSUANCE = auto()
    GENESIS_INITIALIZATION = auto()
    REQUEST_INITIATION = auto()
    REQUEST_MARKED_ENDED = auto()
    REQUEST_SPECIFIC_DOC = auto()


class TransactionActionString(Enum):
    pass


# # Program Metadata
FOLIOBLOCKS_NODE_TITLE: Final[ProgramMetadata] = ProgramMetadata(
    "FolioBlocks - Blockchain Backend (Side | Master) Node API Service (node.py)"
)
FOLIOBLOCKS_NODE_DESCRIPTION: Final[ProgramMetadata] = ProgramMetadata(
    "The backend component of the blockchain system 'folioblocks' | Credential Verification System using Blockchain Technology"
)
FOLIOBLOCKS_EPILOG: Final[ProgramMetadata] = ProgramMetadata(
    "The use of arguments are intended for debugging purposes and development only. Please be careful and be vigilant about the requirements to make certain arguments functioning."
)
FOLIOBLOCKS_HELP: Final[dict[ArgumentParameter, ArgumentDescription]] = {
    ArgumentParameter("DEBUG"): ArgumentDescription(
        "Enables some of the debug features."
    ),
    ArgumentParameter("HOST"): ArgumentDescription(
        "The IP address that this instance is going to allocate from a machine. This should be the base IP address that other nodes should use in order to communicate from each other."
    ),
    ArgumentParameter("KEY_FILE"): ArgumentDescription(
        "A file that contains a set of keys for encrypting and decrypting information for all transaction-related actions. This argument is not required unless the file has a different name."
    ),
    ArgumentParameter("LOCAL"): ArgumentDescription(
        "When specified, run the blockchain node system with hot reload and other elements that enable debug features. Note that this is discouraged since database does not get into the state of locking since hot reload is messing it. I suggest using external hot reloaders."
    ),
    ArgumentParameter("LOG_LEVEL"): ArgumentDescription(
        "Specifies the level to log in both console and to the file (if enabled). Refer to the Logging Levels of Logging Documentation."
    ),
    ArgumentParameter("NO_LOG_FILE"): ArgumentDescription(
        "Disables logging to a file. This assert that the log should be outputted in the CLI."
    ),
    ArgumentParameter("PORT"): ArgumentDescription(
        "Specify the port for this instance. Ensure that this instance is not conflicted with other instances as it will cause to fail before it can get to running its ASGI instance."
    ),
    ArgumentParameter("PREFER_ROLE"): ArgumentDescription(
        f"Assigns a role supplied from this parameter. The role {NodeType.MASTER_NODE.name} can be enforced once. If there's a node that has a role of {NodeType.MASTER_NODE.name} before this node, then assign {NodeType.ARCHIVAL_MINER_NODE.name} to this node."
    ),
}
