"""
Processor Functions (processors.py) | Set of functions that processes a particular object / entity / elements, whatever you call it.

These functions varies from handling file resources and contents of a variable.
Please note that there are no distinctions / categorization (exception for alphabetical) available for each functions, read their description to understand their uses.

This file is part of FolioBlocks.

FolioBlocks is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
FolioBlocks is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with FolioBlocks. If not, see <https://www.gnu.org/licenses/>.
"""

import sys
from asyncio import gather, get_event_loop
from getpass import getpass
from hashlib import sha256
from http import HTTPStatus
from json import dump as json_export
from logging import Logger, getLogger
from os import _exit
from os import environ as env
from os import getpid
from os import kill as kill_process
from pathlib import Path
from secrets import token_hex

from aiohttp import ClientResponse
from aiosmtplib import SMTPException
from blueprint.models import tokens
from blueprint.schemas import (
    AgnosticCredentialValidator,
    ApplicantUserTransaction,
    OrganizationIdentityValidator,
)
from core.constants import (
    REF_MASTER_BLOCKCHAIN_ADDRESS,
    REF_MASTER_BLOCKCHAIN_PORT,
    AddressUUID,
    HTTPQueueMethods,
    JWTToken,
    OrganizationType,
    TokenStatus,
    TransactionContextMappingType,
    URLAddress,
    UserEntity,
)
from core.dependencies import set_master_node_properties
from fastapi import HTTPException
from sqlalchemy.sql.expression import Select

from blueprint.schemas import Block
from core.constants import ConsensusNegotiationStatus

if sys.platform == "win32":
    from signal import CTRL_C_EVENT as CALL_TERMINATE_EVENT
else:
    from signal import SIGTERM as CALL_TERMINATE_EVENT

from sqlite3 import Connection, DatabaseError, OperationalError, connect
from typing import Any, Final, Mapping

from aioconsole import ainput
from aiofiles import open as aopen
from blueprint.models import (
    associations,
    consensus_negotiation,
    file_signatures,
    model_metadata,
    tx_content_mappings,
    users,
)
from core.constants import (
    ASYNC_TARGET_LOOP,
    AUTH_ENV_FILE_NAME,
    BLOCKCHAIN_NAME,
    BLOCKCHAIN_NODE_JSON_TEMPLATE,
    BLOCKCHAIN_RAW_PATH,
    DATABASE_NAME,
    DATABASE_RAW_PATH,
    DATABASE_URL_PATH,
    FERNET_KEY_LENGTH,
    SECRET_KEY_LENGTH,
    CredentialContext,
    CryptFileAction,
    HashedData,
    KeyContext,
    NodeType,
    RawData,
    RuntimeLoopContext,
)
from core.dependencies import get_database_instance, store_db_instance
from cryptography.fernet import Fernet, InvalidToken
from databases import Database
from dotenv import find_dotenv, load_dotenv
from email_validator import EmailNotValidError, EmailSyntaxError, validate_email
from passlib.context import CryptContext
from sqlalchemy import create_engine, func, select
from sqlalchemy.sql.expression import ClauseElement, Delete, Insert, Select

from utils.exceptions import NoKeySupplied, UnsatisfiedClassType
from utils.http import get_http_client_instance

logger: Logger = getLogger(ASYNC_TARGET_LOOP)
pwd_handler: CryptContext = CryptContext(schemes=["bcrypt"])

# # File Handlers, Cryptography — START
async def crypt_file(
    *,
    filename: str,
    key: KeyContext,
    process: CryptFileAction,
    return_key: bool = False,
    return_file_hash: bool = False,
    enable_async: bool = False,
) -> bytes | str | None:
    """
    A Non-async function that processes a file with `to` under `filename` that uses `key` for decrypt and encrypt processes. This function exists for providing anti-redundancy over calls for preparing the files that has to be initialized for the session. This function is not compatible during async process, please refer to the acrypt_file for the implementation of async version.
    """

    if not isinstance(process, CryptFileAction):
        raise UnsatisfiedClassType(process, CryptFileAction)

    processed_content: bytes = b""
    crypt_context: Fernet | None = None
    file_content: str | bytes = ""

    # Open the file first.
    file_content = await process_crpyt_file(
        is_async=enable_async, filename=filename, mode="rb"
    )

    try:
        logger.debug(
            f"{'Async: ' if enable_async else ''}{'Decrypting' if process == CryptFileAction.TO_DECRYPT else 'Encrypting'} a context ..."
        )
        if process == CryptFileAction.TO_DECRYPT:
            if key is None:
                raise NoKeySupplied(
                    crypt_file,
                    "Decryption operation cannot continue due to not having a key.",
                )

            crypt_context = Fernet(key.encode("utf-8") if isinstance(key, str) else key)

        else:
            if key is None:
                key = Fernet.generate_key()

            crypt_context = Fernet(key)

        processed_content = getattr(
            crypt_context,
            "decrypt" if process == CryptFileAction.TO_DECRYPT else "encrypt",
        )(file_content)

        # Then write to the file for the final effect.
        await process_crpyt_file(
            content_to_write=processed_content,
            filename=filename,
            is_async=enable_async,
            mode="wb",
        )

        logger.info(
            f"Successfully {'decrypted' if process == CryptFileAction.TO_DECRYPT else 'encrypted'} a context."
        )

        if return_key and not return_file_hash and isinstance(key, bytes):
            return key

        elif not return_key and return_file_hash:
            _file_content: bytes | str = (
                file_content
                if process == CryptFileAction.TO_DECRYPT
                else processed_content
            )

            if isinstance(_file_content, str):
                _file_content = _file_content.encode("utf-8")

            if isinstance(_file_content, bytes):
                return sha256(_file_content).hexdigest()

    except InvalidToken:
        logger.critical(
            f"{'Decryption' if process == CryptFileAction.TO_DECRYPT else 'Encryption'} failed. This may likely corrupted your file! Please check your argument and try again after reloading the backup. If persists, please report to the developer."
        )
        _exit(1)


async def process_crpyt_file(
    *,
    is_async: bool,
    filename: str,
    mode: Any,  # Cannot import Literals for the aiofiles.mode here.
    content_to_write: Any = None,
) -> str | bytes:

    # * In the near future, we can do something about this one.
    resolved_fn_name: str = "read" if mode == "rb" else "write"

    if is_async:
        # * I cannot deduce this by DRY.
        async with aopen(filename, mode) as acontent_buffer:
            if mode == "wb":
                file_content: str | bytes = await getattr(
                    acontent_buffer, resolved_fn_name
                )(content_to_write)
            else:
                file_content = await getattr(acontent_buffer, resolved_fn_name)()
    else:
        with open(filename, mode) as content_buffer:
            if mode == "wb":
                file_content = getattr(content_buffer, resolved_fn_name)(
                    content_to_write
                )
            else:
                file_content = getattr(content_buffer, resolved_fn_name)()

    return file_content


# # File Handlers, Cryptography — END

# # File Resource Initializers and Validators, Blockchain and Database — START
async def initialize_resources_and_return_db_context(
    *,
    runtime: RuntimeLoopContext,
    role: NodeType,
    auth_key: KeyContext = None,
) -> Database:
    """
    A non-async initializer for both database and blockchain files.

    Intializes the file by decryption when async thread is not yet initialized.
    For new instance, generate a new file end encrypt them to return an ID that can be decrypt later.

    Args:
        runtime (RuntimeLoop): The runtime context, this is evaluated from __name__.
        keys (tuple[KeyContext, KeyContext] | None, optional): The value of the key that is parsed from the argparse library. Defaults to None.

    Returns:
        Database | None: Returns the context of the database for accessing the tables. Which can be ORM-accessible.
    """

    logger.info("Initializing a database ...")
    db_instance: Database = Database(DATABASE_URL_PATH)
    sql_engine = create_engine(
        DATABASE_URL_PATH, connect_args={"check_same_thread": False}
    )

    db_file_ref: Path = Path(DATABASE_RAW_PATH)
    bc_file_ref: Path = Path(BLOCKCHAIN_RAW_PATH)

    file_folder = Path(f"{Path(__file__).cwd()}/userfiles")

    if not file_folder.exists():
        file_folder.mkdir(parents=True, exist_ok=False)

    logger.debug(
        f"SQL Engine Connector (Reference) and Async Instance for the {DATABASE_URL_PATH} has been instantiated."
    )

    if runtime == "__main__":

        # - This is just an additional checking.
        if (db_file_ref.is_file() and bc_file_ref.is_file()) and auth_key is not None:
            con: Connection | None = None
            logger.info("Decrypting the database ...")
            await crypt_file(
                filename=DATABASE_RAW_PATH,
                key=auth_key,
                process=CryptFileAction.TO_DECRYPT,
            )

            try:
                con = connect(DATABASE_RAW_PATH)
                store_db_instance(db_instance)
                logger.info("Database instance has been saved in-memory.")

            except OperationalError as e:
                logger.error(
                    f"Database is potentially corrupted or missing. | Additional Info: {e}"
                )
                _exit(1)

            finally:
                logger.info("Database decrypted.")
                if con is not None:
                    con.close()

            await db_instance.connect()
            logger.warning(
                "Temporarily opened the database connection from instance to check integrity of the blockchain file contents."
            )

            """
            - Understood that this was duplicated from the <class `BlockchainMechanism`>
            - I cannot access that instance beyond this point due to the fact that we had multiple checks before instantiating important objects.
            """
            blockchain_validate_hash_query: Select = select(
                [file_signatures.c.hash_signature]
            ).where(file_signatures.c.filename == BLOCKCHAIN_NAME)
            blockchain_retrieved_hash: Mapping = await db_instance.fetch_val(
                blockchain_validate_hash_query
            )
            logger.info("Fetched blockchain file content's signature.")

            # * We need to decrypt the blockchin file first before we do something to it. If we didn't, we are technically reading the encrypted version instead of the exposed version.
            await crypt_file(
                filename=BLOCKCHAIN_RAW_PATH,
                key=auth_key,
                process=CryptFileAction.TO_DECRYPT,
            )
            logger.info("Blockchain file decrypted.")

            with open(BLOCKCHAIN_RAW_PATH, "rb") as blockchain_content:
                blockchain_context_hash = sha256(blockchain_content.read()).hexdigest()

            if blockchain_context_hash != blockchain_retrieved_hash:
                # @o Despite mismatched, we can just fetch a new one from the NodeType.MASTER_NODE.

                logger.critical(
                    f"Blockchain's file content signature were mismatch! Database: {blockchain_retrieved_hash} | Computed: {blockchain_context_hash} | This will be refreshed upon consensus negotiation with the {NodeType.MASTER_NODE.name}."
                )
            else:
                logger.info("Blockchain file content signature is valid!")

            await db_instance.disconnect()

            return db_instance

        elif (db_file_ref.is_file() and bc_file_ref.is_file()) and auth_key is None:
            logger.critical(
                f"A database exists but there's no key inside of {AUTH_ENV_FILE_NAME} or the file ({AUTH_ENV_FILE_NAME}) is missing. Have you modified it? Please check and try again."
            )
            _exit(1)

        elif (
            not db_file_ref.is_file() or bc_file_ref.is_file()
        ) and auth_key is not None:
            logger.critical(
                "Hold up! You seem to have a key but don't have a database or the blockchain. Have you modified the directory? If so, please put the database back (encrypted) and try again. Otherwise, delete the key and try again if you are attempting to create a new instance."
            )
            _exit(1)

        else:
            logger.warning(
                f"Database and blockchain file does not exists. Creating such resources, a new database -> `{DATABASE_NAME}` and blockchain -> `{BLOCKCHAIN_NAME}`."
            )

            # - Create the model in-memory to structurize the database file.
            model_metadata.create_all(sql_engine)
            logger.info("Database structurized from SQLAlchemy.")

            auth_key = await crypt_file(
                filename=DATABASE_RAW_PATH,
                key=auth_key,
                process=CryptFileAction.TO_ENCRYPT,
                return_key=True,
            )
            logger.info("Database has been encrypted to gain the `auth_key`.")

            if auth_key is None:
                raise NoKeySupplied(
                    initialize_resources_and_return_db_context,
                    "This part of the function should have a returned new `auth_key`. This was not intended! Please report this issue as soon as possible!",
                )

            await crypt_file(
                filename=DATABASE_RAW_PATH,
                key=auth_key,
                process=CryptFileAction.TO_DECRYPT,
            )
            logger.warning("Temporarily decrypted database to insert signature data.")

            # - Write the initial blockchain file.
            with open(BLOCKCHAIN_RAW_PATH, "w") as temp_writer:
                initial_json_context: dict[
                    str, list[Any]
                ] = BLOCKCHAIN_NODE_JSON_TEMPLATE

                json_export(initial_json_context, temp_writer)
            logger.info("Initial blockchain file has been written.")

            # - Even though we already write from the file, we have to look at its decrypted form
            # - As we value its actual content, not the hashed form.
            with open(BLOCKCHAIN_RAW_PATH, "rb") as chain_temp_reader:
                raw_blockchain_hash = sha256(chain_temp_reader.read()).hexdigest()

            # - Insert the resulting hash from the database.
            blockchain_hash_query: Insert = file_signatures.insert().values(
                filename=BLOCKCHAIN_NAME, hash_signature=raw_blockchain_hash
            )
            logger.info("Initial blockchain signature has been calculated.")

            # - Connect to the database, and then execute the SQL command.
            await gather(
                db_instance.connect(), db_instance.execute(blockchain_hash_query)
            )

            logger.info("Database insertion of blockchain signature is done.")

            await crypt_file(
                filename=BLOCKCHAIN_RAW_PATH,
                key=auth_key,
                process=CryptFileAction.TO_ENCRYPT,
            )
            logger.info("Blockchain file has been encrypted.")

            await crypt_file(
                filename=DATABASE_RAW_PATH,
                key=auth_key,
                process=CryptFileAction.TO_ENCRYPT,
            )
            logger.info("Database file has been encrypted.")

            logger.warning(
                f"To re-iterate, the system detects the invocation of role as a {role.name}. {'Please insert email address and password for the email services.'  if role is NodeType.MASTER_NODE else 'The system will attempt to generate `AUTH_KEY` and `SECRET_KEY`.'}"
            )
            if role is NodeType.MASTER_NODE:
                logger.warning(
                    "Please ENSURE that credentials are correct. Don't worry, it will be hashed along with the `auth_key` that is generated here."
                )

                credentials: list[CredentialContext] = await ensure_input_prompt(
                    input_context=["SERVER Email Address", "SERVER Email Password"],
                    hide_input_from_field=[False, True],
                    generalized_context="Server email credentials",
                    additional_context=f"There's no going back once proceeded. Though, you can review and change the credentials by looking at the `{AUTH_ENV_FILE_NAME}`.",
                )

            with open(AUTH_ENV_FILE_NAME, "w") as env_writer:
                env_context: list[str] = [
                    f"AUTH_KEY={auth_key.decode('utf-8')}",
                    f"SECRET_KEY={token_hex(32)}",
                ]

                if role is NodeType.MASTER_NODE:
                    env_context.append(f"EMAIL_SERVER_ADDRESS={credentials[0]}")
                    env_context.append(f"EMAIL_SERVER_PWD={credentials[1]}")

                for each_context in env_context:
                    env_writer.write(each_context + "\n")

            logger.info(
                f"Generated keys were saved to the environment file (`{AUTH_ENV_FILE_NAME}`)."
            )

            logger.info(
                f"Initial setup is done. Double-check for readable-credentials if they were finalized. PLEASE DO NOT SHARE THOSE CREDENTIALS. | You need to relaunch this program so that the program will load the generated keys from the file."
            )
            _exit(0)

    store_db_instance(db_instance)
    return db_instance


async def close_resources(*, key: KeyContext) -> None:
    """
    Asynchronous Database Close Function.

    Async-ed since on_event("shutdown") is under async scope and does
    NOT await non-async functions.
    Closes the state of the database by encrypting it back to the uninitialized state.

    Args:
        key (KeyContext): The key that is recently used for decrypting the SQLite database.

    """
    db: Database = get_database_instance()

    logger.warning(
        f"Ensuring encode process of computed hash-signature for the `{BLOCKCHAIN_NAME}`."
    )

    logger.warning("Closing blockchain by encryption ...")
    await crypt_file(
        filename=BLOCKCHAIN_RAW_PATH,
        key=key,
        process=CryptFileAction.TO_ENCRYPT,
        enable_async=True,
        return_file_hash=True,
    )

    logger.warning("Closing database by encryption ...")
    await db.disconnect()  # * Shutdown the database instance.    db.execute()
    await crypt_file(
        filename=DATABASE_RAW_PATH,
        key=key,
        process=CryptFileAction.TO_ENCRYPT,
        enable_async=True,
    )
    logger.info("Database and blockchain successfully closed and encrypted.")

    supress_exceptions_and_warnings()
    await get_event_loop().shutdown_default_executor()


file_ref: str  # - This is needed to avoid complicated implementation, but ugly.


def load_env(*, reload: bool = False) -> None:
    try:
        load_dotenv(
            find_dotenv(filename=str(Path(file_ref)), raise_error_if_not_found=True)
        )

    except OSError:
        if not reload:
            exit(
                f"The file {file_ref} may not be a environment file or is missing. Please check your arguments or the file."
            )
        logger.error(
            f"The environment variables cannot be loaded as the environment file '{file_ref}' is missing."
        )


def validate_file_keys(
    context: KeyContext | None,
) -> tuple[KeyContext, KeyContext]:

    global file_ref
    file_ref = f"{Path(__file__).cwd()}/{context}"

    # - Validate if the given context is a path first.
    if Path(file_ref).is_file():

        load_env()

        a_key: KeyContext = env.get("AUTH_KEY", None)
        s_key: KeyContext = env.get("SECRET_KEY", None)

        # Validate the (AUTH_KEY and SECRET_KEY)'s length.
        if (
            a_key is not None
            and a_key.__len__() == FERNET_KEY_LENGTH
            or s_key is not None
            and s_key.__len__() == SECRET_KEY_LENGTH
        ):

            return a_key, s_key

        raise NoKeySupplied(
            validate_file_keys,
            f"Error: One of the keys either has an invalid value or is missing. Have you modified your {file_ref}? Please check and try again.",
        )


# # File Resource Initializers and Validators, Blockchain and Database — END

# # Variable Password Crypt Handlers — START
def hash_context(*, pwd: RawData) -> HashedData:
    return pwd_handler.hash(pwd)


def verify_hash_context(*, real_pwd: RawData, hashed_pwd: HashedData) -> bool:
    return pwd_handler.verify(real_pwd, hashed_pwd)


async def ensure_input_prompt(
    *,
    input_context: list[Any] | Any,
    hide_input_from_field: list[bool] | bool,
    generalized_context: str,
    additional_context: str | None = None,
    enable_async: bool = False,
    delimiter: str = ":",
) -> Any:
    """
    Ensures that a there will be an input / prompt for the user to interact.
    Each `input_context` will be prompted, along with their properties such as `hide_input_fields` were rendered.

    Note that this also renders input field to be asynchronous by `enable_async` by choice.
    There are also configurations added as well for styling of the prompt.

    Args:
        input_context (list[Any] | Any): The string / a set of string that represents the field.
        hide_fields (list[bool] | bool): A field / a set of fields that hides the input.
        generalized_context (str): The string to display upon confirmation if their input is final.
        additional_context (str | None, optional): Additional information added to the prompt upon finalization of inputs. Defaults to None.
        enable_async (bool, optional): Allows to `await` this function or `run_in_executor` if false.. Defaults to False.
        delimiter (_type_, optional): Basically, a divider. Defaults to ":".

    Returns:
        Any: _description_
    """

    # * Assert in list form for all readable type.
    assert_lvalue: int = len(
        input_context if isinstance(input_context, list) else [input_context]
    )
    assert_rvalue: int = len(
        hide_input_from_field if isinstance(input_context, list) else [hide_input_from_field]  # type: ignore # ??? | Resolve the `Sized` incompatibility with bool.
    )
    assert (
        assert_lvalue == assert_rvalue
    ), f"The `input_context` (length of {assert_lvalue}) and the `hide_fields` (length of {assert_rvalue}) were unequal! This is a developer issue, please report as possible."

    while True:
        input_s: list[str] | str = "" if isinstance(input_context, str) else []

        # # Implementation-wise, I understand that the code below is too redundant, but I can't fix it as of now.

        if isinstance(input_context, list) and isinstance(hide_input_from_field, list):
            for field_idx, each_context_to_input in enumerate(input_context):
                while True:
                    _item_input = await handle_input_function(
                        awaited=enable_async,
                        input_hidden=hide_input_from_field[field_idx],
                        message=f"{each_context_to_input}{delimiter} ",
                    )

                    if not _item_input:
                        logger.error(
                            f"One of the inputs for the `{generalized_context}` is empty! Please try again."
                        )
                        continue

                    keyword_n_input_validate = verify_email_keyword_and_validate_input(
                        display=f"{each_context_to_input}{delimiter} ",
                        inputted=_item_input,
                    )
                    if keyword_n_input_validate[0] and not keyword_n_input_validate[1]:
                        continue

                    if isinstance(input_s, list):
                        input_s.append(_item_input)

                    break

        else:
            if isinstance(hide_input_from_field, bool):
                input_s = await handle_input_function(
                    awaited=enable_async,
                    input_hidden=hide_input_from_field,
                    message=f"{input_context}{delimiter} ",
                )
            else:
                unconventional_terminate(
                    message=f"Assertion Error: Input hidden is not a type 'bool'. This condition scope does not expect type {type(hide_input_from_field)}."
                )

            if not input_s:
                logger.error(
                    f"The input for the {generalized_context} is empty! Please try again."
                )
                continue

            singleton_keyword_n_value_validate = (
                verify_email_keyword_and_validate_input(
                    display=f"{input_context}{delimiter} ",
                    inputted=input_s if isinstance(input_s, str) else "",
                )
            )

            if (
                singleton_keyword_n_value_validate[0]
                and not singleton_keyword_n_value_validate[1]
            ):
                continue

        logger.warning(
            f"Are you sure you this is the right{(' ' + generalized_context) if generalized_context is not None else ''}? {additional_context}"
        )

        ensure: str = input(
            f"[Press ENTER to continue / type 'N' or 'n' to re-type {generalized_context}] > "
        )

        if ensure == "n" or ensure == "N":
            continue

        return input_s


def verify_email_keyword_and_validate_input(
    *, display: str, inputted: str
) -> tuple[bool, bool]:
    email_input_indicators: Final[list[str]] = [
        "Email address",
        "email address",
        "E-mail address",
        "e-mail address",
        "EMail address",
        "Email Address",
        "email Address",
        "E-mail Address",
        "e-mail Address",
        "EMail Address",
    ]
    if any(each_keyword in display for each_keyword in email_input_indicators):
        try:
            validate_email(inputted)
            logger.info("E-mail address is valid!")
            return (
                True,
                True,
            )  # @o Since `validate_email` doesn't return a bool but rather a context, then we assume its good, therefore return `True`.

        except (EmailNotValidError, EmailSyntaxError) as e:
            logger.error(
                f"Invalid e-mail address! Please try again | Additional Info: {e}."
            )
            return (True, False)

    return (False, False)


async def handle_input_function(
    *, awaited: bool, input_hidden: bool, message: str
) -> str:
    """
    Technically a handler to the input that is being called by ensure_input_prompt.

    Seperated since list form and singleton parameter uses the same mechanism.

    Args:
        awaited (bool): Is the input being awaited `was async` or not?
        input_hidden (bool): Is the input hidden or not?
        message (str): The message to display incorporated with the input.
    """
    event_loop_ref = get_event_loop()

    if not input_hidden and not awaited:
        _ireturned: str = input(message)

    elif input_hidden and awaited:
        _ireturned = await event_loop_ref.run_in_executor(None, getpass, message)

    elif not input_hidden and awaited:
        _ireturned = await ainput(message)

    else:  # ! Resolves to `input_hidden` and not `awaited`.
        _ireturned = getpass(message)

    return _ireturned


# # Variable Password Crypt Han1dlers — END


# # Blockchain
async def contact_master_node(*, master_host: str, master_port: int) -> None:
    logger.info(
        f"Attempting to contact the {NodeType.MASTER_NODE.name} at host {master_host} in port {master_port} ..."
    )

    master_node_response: ClientResponse = (
        await get_http_client_instance().enqueue_request(
            url=URLAddress(f"{master_host}:{master_port}/explorer/chain"),
            method=HTTPQueueMethods.GET,
            await_result_immediate=True,
            retry_attempts=99,
            return_on_error=False,
            name="contact_master_node",
        )
    )

    if master_node_response.ok:
        # - Since we do understand that it may be a `MASTER` node, then save its URL then attempt to negotiate by logging to them later.
        set_master_node_properties(
            key=REF_MASTER_BLOCKCHAIN_ADDRESS, context=master_host
        )
        set_master_node_properties(key=REF_MASTER_BLOCKCHAIN_PORT, context=master_port)

        logger.info(f"Master node responded at {master_host}:{master_port}!")


# # This may be moved inside BlockchainMechanism.
async def look_for_archival_nodes() -> None:
    logger.error("This function is NotYetImplemented.")


# # Input Stoppers — START
def supress_exceptions_and_warnings() -> None:
    sys.tracebacklimit = 0


def unconventional_terminate(*, message: str, early: bool = False) -> None:
    """A method that terminates the runtime process unconventionally via calling signal or `exit()`.

    Args:
        message (str): The message to display under `logging.critical(<context>).`
        early (bool): Indicates that this method were running BEFORE the ASGI instantiated. Invoking this will not run other co-corotines while uvicorn receives the 'signal.CTRL_C_EVENT'.
    """

    logger.critical(message)
    if early:
        supress_exceptions_and_warnings()
        exit(-1)

    kill_process(getpid(), CALL_TERMINATE_EVENT)


# # Input Stoppers — END

# # Output Filters — START
def mask(data: bytes | int | str) -> str:
    if isinstance(data, int):
        _data = data.__str__()
    elif isinstance(data, bytes):
        _data = data.decode("utf-8")
    else:
        _data = data

    return "*" * len(_data)


# # Output Filters — END

# # API DRY Handler — START
async def validate_applicant_user_address(
    *, supplied_address: AddressUUID, expected_type: UserEntity
) -> None:

    if isinstance(supplied_address, str):
        address_existence_checker_query: Select = select([func.count()]).where(
            (users.c.unique_address == supplied_address)
            & (users.c.type == expected_type)
        )

        address: Mapping | None = await get_database_instance().fetch_one(
            address_existence_checker_query
        )

        if not address.count:  # type: ignore
            raise HTTPException(
                detail="Supplied address reference does not exist. Please check your input and try again.",
                status_code=HTTPStatus.NOT_FOUND,
            )

        return None

    raise HTTPException(
        detail=f"Supplied address is an invalid object. Please ensure that the address is a type of {type(str)}.",
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
    )


# # -----------------------------------------------------


async def validate_organization_existence(
    *, org_identity: OrganizationIdentityValidator, scoped_to_applicants: bool
) -> Mapping | None:

    # - Specific instances of whether the organization is classified as non-educational or otherwise, each cases of it requires a different parameter or query to validate the existence of the association/organization.
    # @o For the instance of `OrganizationUserTransaction` it checks the `association_address` if given (in the scenario that the association/organiaztion does exists), or it was checked by `association_name` and `association_group_type.` (in the scenario where the association/organization does not exists and requires a new one)
    # ! Therefore, the way its variables are declared is when the organization does not exists or not.

    # @d The switch `scope_to_applicants` forces to resolve the given parameter in 'org_identity', which is an address from the user, NOT a reference address from the association, by setting `scope_to_applicants` to `True`, it queries that address if the association exists based from the address of source.
    # @d It does not forces to query along both types along with the address, when the instance is `ApplicantUserTransacion`.

    database_instance: Database = get_database_instance()
    resolved_association_ref_from_user: Mapping | str | None = (
        org_identity.association_address
    )

    if scoped_to_applicants:
        get_association_query: Select = select([users.c.association]).where(
            users.c.unique_address == org_identity.association_address
        )

        resolved_association_ref_from_user = await database_instance.fetch_val(
            get_association_query
        )

    validate_association_existence_query: Select = select(
        [associations.c.address]
    ).where(
        (
            (associations.c.address == resolved_association_ref_from_user)
            if scoped_to_applicants
            else (
                (associations.c.address == resolved_association_ref_from_user)
                | (
                    (associations.c.name == org_identity.association_name)
                    & (
                        (associations.c.group == OrganizationType.INSTITUTION)
                        | (associations.c.group == OrganizationType.ORGANIZATION)
                    )
                )
            )
        )
    )

    existing_association: Mapping | None = await database_instance.fetch_val(
        validate_association_existence_query
    )

    return existing_association


async def validate_previous_consensus_negotiation(
    *,
    database_instance_ref: Database,
    block_reference: Block,
) -> None:
    previous_negotiation_sql_ref: ClauseElement = (
        consensus_negotiation.c.block_no_ref == block_reference.id
    )

    # - Check for existing incomplete negotiation.
    existing_negotiation_query: Select = select([consensus_negotiation.c.id]).where(
        previous_negotiation_sql_ref
    )

    existing_negotiation = await database_instance_ref.fetch_val(
        existing_negotiation_query
    )

    if existing_negotiation is not None:
        # - Assume this is incomplete, we delete it to insert a new consensus negotiation.
        delete_previous_negotiation_query: Delete = (
            consensus_negotiation.delete().where(previous_negotiation_sql_ref)
        )
        await database_instance_ref.execute(delete_previous_negotiation_query)


async def validate_source_and_origin_associates(
    database_instance_ref: Database,
    source_session_token: JWTToken,
    target_address: AddressUUID | None,
    skip_validation_on_target: bool,
    return_resolved_source_address: bool,
) -> AddressUUID | None:

    # * Evaluate if there's a need to skip validating target address.
    # ! Some models doens't have a target address by default, with that, we may only need to validate the source address.
    should_skip_validation: bool = skip_validation_on_target and not isinstance(
        target_address, str
    )  # * And since it may be skipped, should the target address is not a string.

    # - Ensure no ambigous condition by validating the `target_address` parameter.
    if skip_validation_on_target and isinstance(target_address, str):
        raise HTTPException(
            detail="Skipping validation but the target address is specified, prohibited to avoid conflicting other conditions.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    # - Validate the token of the one who sent this transaction and receive the address.
    get_sender_address_via_token_query: Select = select([tokens.c.from_user]).where(
        (tokens.c.token == source_session_token)
        & (tokens.c.state == TokenStatus.CREATED_FOR_USE)
    )
    resolved_source_address = await database_instance_ref.fetch_val(
        get_sender_address_via_token_query
    )

    if resolved_source_address == target_address:
        raise HTTPException(
            detail="Self-casting additional information is not possible!",
            status_code=HTTPStatus.CONFLICT,
        )

    # - Validate the provided target address by fetching the association reference.
    validate_target_address_query: Select = select([users.c.association]).where(
        (users.c.unique_address == target_address)
    )

    resolved_target_address_as_association = await database_instance_ref.fetch_val(
        validate_target_address_query
    )

    # - Once done, check if the database returns something.
    if resolved_source_address is None:
        raise HTTPException(
            detail="The user may be impossibly alive due to the token's state of being inactive or labelled as expired or does not exists.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    if resolved_target_address_as_association is None and not should_skip_validation:
        raise HTTPException(
            detail="The target address does not exists.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    # - Since the target address contains the association (most likely), then get the source address.
    get_source_address_association: Select = select([users.c.association]).where(
        (users.c.unique_address == resolved_source_address) & (users.c.type == UserEntity.ORGANIZATION_DASHBOARD_USER)  # type: ignore
    )

    source_address_association = await database_instance_ref.fetch_val(
        get_source_address_association
    )

    if source_address_association is None:
        raise HTTPException(
            detail=f"Given token resolving to user (either both `source` and `target` users / addresses) fails to be resolved or the given type of an existing user is not allowed.",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    # - Ensure that these users are connected only from this organization.
    if (
        source_address_association != resolved_target_address_as_association
    ) and not should_skip_validation:
        raise HTTPException(
            detail="The source or target address has a different organization!",
            status_code=HTTPStatus.NOT_ACCEPTABLE,
        )

    # - Ensure that these users are connected from their association.
    check_source_address_associate_query: Select = select([func.count()]).where(
        associations.c.address == source_address_association
    )

    source_user_validity = await database_instance_ref.fetch_one(
        check_source_address_associate_query
    )

    check_target_user_associate_query: Select = select([func.count()]).where(
        associations.c.address == source_address_association
    )

    target_user_validity = await database_instance_ref.fetch_one(
        check_target_user_associate_query
    )

    if not source_user_validity.count and (  # type: ignore
        not target_user_validity.count and not skip_validation_on_target  # type: ignore
    ):
        raise HTTPException(
            detail=f"The source or the target (address) user is not associated with any of the associations/organizations!",
            status_code=HTTPStatus.NOT_ACCEPTABLE,
        )

    # - Last check, ensure that these targets contains transaction mapping that states that they have a content from the blockchain.

    check_source_address_tx_map: Select = select([func.count()]).where(
        (tx_content_mappings.c.address_ref == resolved_source_address)
        & (
            tx_content_mappings.c.content_type
            == TransactionContextMappingType.ORGANIZATION_BASE
        )
    )

    check_target_address_tx_map: Select = select([func.count()]).where(
        (tx_content_mappings.c.address_ref == resolved_target_address_as_association)
        & (
            tx_content_mappings.c.content_type
            == TransactionContextMappingType.APPLICANT_BASE
        )
    )

    source_address_tx_map = await database_instance_ref.fetch_one(
        check_source_address_tx_map
    )

    target_address_tx_map = await database_instance_ref.fetch_one(
        check_target_address_tx_map
    )

    if source_address_tx_map.count and (  # type: ignore
        target_address_tx_map.count  # type: ignore
        and not skip_validation_on_target
        and not isinstance(target_address, str)
    ):
        raise HTTPException(
            detail="The source or the target address doesn't have a transaction mapping from the blockchain, this is illegal!",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return AddressUUID(resolved_source_address) if return_resolved_source_address else None  # type: ignore


async def validate_transaction_mapping_exists(
    *, user_address: AddressUUID | str, content_type: TransactionContextMappingType
) -> bool:

    if content_type in [
        TransactionContextMappingType.APPLICANT_BASE,
        TransactionContextMappingType.ORGANIZATION_BASE,
    ]:

        resolved_reference_group: UserEntity = (
            UserEntity.APPLICANT_DASHBOARD_USER
            if content_type is TransactionContextMappingType.APPLICANT_BASE
            else UserEntity.ORGANIZATION_DASHBOARD_USER
        )

        await validate_applicant_user_address(
            supplied_address=AddressUUID(user_address),
            expected_type=resolved_reference_group,
        )

        find_tx_mapping_query_query: Select = select([func.count()]).where(
            (tx_content_mappings.c.address_ref == user_address)
            & (tx_content_mappings.c.content_type == content_type)
        )

        found_tx_mapping: Mapping | None = await get_database_instance().fetch_one(
            find_tx_mapping_query_query
        )

        return True if found_tx_mapping.count else False  # type: ignore

    # - Even this method returns `False`, this is an internal error logic that should hit any APIs associated from this method.
    raise HTTPException(
        detail="There was an error regarding transaction validation mappin, please report this to the administrators to fix this issue.",
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


async def validate_user_existence(
    *, user_identity: AgnosticCredentialValidator
) -> bool:
    validate_existence_user_query: Select = select([func.count()]).where(
        (users.c.first_name == user_identity.first_name)
        & (users.c.last_name == user_identity.last_name)
        & (users.c.username == user_identity.username)
        & (users.c.email == user_identity.email)
    )

    existing_user: Mapping | None = await get_database_instance().fetch_one(
        validate_existence_user_query
    )

    if not existing_user.count:  # type: ignore
        return False

    return True


# # Blockchain DRY Handlers — END
