"""
API — Explorer and Node API for the Master Node.

This file is part of FolioBlocks.

FolioBlocks is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
FolioBlocks is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with FolioBlocks. If not, see <https://www.gnu.org/licenses/>.
"""


from http import HTTPStatus
from typing import Any

from sqlalchemy import select

from blueprint.schemas import NodeConsensusInformation
from core.blockchain import get_blockchain_instance
from core.constants import AddressUUID, BaseAPI, NodeAPI, UserEntity
from core.dependencies import (
    EnsureAuthorized,
    get_identity_tokens,
)
from fastapi import APIRouter, Depends, HTTPException, Header
from core.constants import AuthAcceptanceCode, JWTToken
from core.dependencies import get_database_instance
from blueprint.models import auth_codes, tokens, users

node_router = APIRouter(
    prefix="/node",
    tags=[BaseAPI.NODE.value],
)


@node_router.get(
    "/info",
    tags=[
        NodeAPI.GENERAL_NODE_API.value,
        NodeAPI.NODE_TO_NODE_API.value,
        NodeAPI.MASTER_NODE_API.value,
    ],
    response_model=NodeConsensusInformation,
    summary="Fetch information from the master node.",
    description="An API endpoint that returns information based on the authority of the client's requests. This requires special headers.",
    dependencies=[
        Depends(
            EnsureAuthorized(
                _as=[UserEntity.ARCHIVAL_MINER_NODE_USER, UserEntity.MASTER_NODE_USER]
            )
        ),
    ],
)
async def get_node_info() -> NodeConsensusInformation:
    blockchain_state: dict[
        str, Any
    ] = get_blockchain_instance().get_blockchain_private_state()

    identity_tokens = get_identity_tokens()

    if identity_tokens is not None:
        node_address = identity_tokens[0]

        return NodeConsensusInformation(
            owner=AddressUUID(node_address),
            is_sleeping=blockchain_state["sleeping"],
            is_mining=blockchain_state["mining"],
            node_role=blockchain_state["role"],
            consensus_timer=blockchain_state["consensus_timer"],
            last_mined_block=blockchain_state["last_mined_block"],
        )

    raise HTTPException(
        detail="Identity tokens from this node is missing. This is a developer-logic issue. Please report this problem as possible.",
        status_code=HTTPStatus.FORBIDDEN,
    )


"""
/consensus/echo | When received ensure its the master by fetching its info.
/consensus/acknowledge | When acknowledging, give something, then it will return something.

# Note that MASTER will have to do this command once! Miners who just finished will have to wait and keep on retrying.
/consensus/negotiate | This is gonna be complex, on MASTER, if there's current negotiation then create a new one (token). Then return a consensus as initial from the computation of the consensus_timer.
/consensus/negotiate | When there's already a negotiation, when called by MASTER, return the context of the consensus_timer and other properties that validates you of getting the block when you are selected.
/consensus/negotiate | When block was fetched then acknowledge it.
/consensus/negotiate | When the miner is done, call this one again but with a payload, and then keep on retrying, SHOULD BLOCK THIS ONE.
/consensus/negotiate | When it's done, call this again for you to sleep by sending the calculated consensus, if not right then the MASTER will send a correct timer.
/consensus/negotiate | Repeat.
# TODO: Actions should be, receive_block, (During this, one of the assert processes will be executed.)
"""

"""
# Node-to-Node Consensus Blockchain Operation Endpoints

@o Whenever the blockchain's `MASTER_NODE` is looking for `ARCHIVAL_MINER_NODE`s. It has to ping them in a way that it shows their availability.
@o However, since we already did some established connection between them, we need to pass them off from the `ARCHIVAL_MINER_NODE`s themselves to the
@o `MASTER_NODE`. This was to ensure that the node under communication is not a fake node by providing the `AssociationCertificate`.

! These endpoints are being used both.
"""

# @node_router.post(
#     "/consensus/receive_echo",
#     tags=[NodeAPI.NODE_TO_NODE_API.value],
#     summary="Receives echo from the `ARCHIVAL_MINER_NODE` for establishment of their connection to the blockchain.",
#     description=f"An API endpoint that is only accessile to {UserEntity.MASTER_NODE_USER.name}, where it accepts ECHO request to fetch a certificate before they ({UserEntity.ARCHIVAL_MINER_NODE_USER}) start doing blockchain operations. This will return a certificate as an acknowledgement response from the requestor.",
#     dependencies=[
#         Depends(
#             EnsureAuthorized(
#                 _as=UserEntity.MASTER_NODE_USER
#             )
#         )
#     ],
# )
# async def acknowledge_as_response(x,x_acceptance) -> None:
#     return


"""
# Node-to-Node Establish Connection Endpoints

@o Before doing anything, an `ARCHIVAL_MINER_NODE` has to establish connection to the `MASTER_NODE`.
@o With that, the `ARCHIVAL_MINER_NODE` has to give something a proof, that shows their proof of registration and login.
@o The following are required: `JWT Token`, `Source Address`, and `Auth Code` (as Auth Acceptance Code)

- When the `MASTER_NODE` identified those tokens to be valid, it will create a special token for the association.
- To-reiterate, the following are the structure of the token that is composed of the attributes between the communicator `ARCHIVAL_MINER_NODE` and the `MASTER_NODE`.
- Which will be the result of the entity named as `AssociationCertificate`.

@o From the `ARCHIVAL_MINER_NODE`: (See above).
@o From the `MASTER_NODE`: `ARCHIVAL_MINER_NODE`'s keys + AUTH_KEY (1st-Half, 32 characters) + SECRET_KEY(2nd-half, 32 character offset, 64 characters)

# Result: AssociationCertificate for the `ARCHIVAL_MINER_NODE` in AES form, whereas, the key is based from the ARCHIVAL-MINER_NODE's keys + SECRET_KEY + AUTH_KEY + DATETIME (in ISO format).

! Note that the result from the `MASTER_NODE` is saved, thurs, using `datetime` for the final key is possible.

- When this was created, `ARCHIVAL_MINER_NODE` will save this under the database and will be used further with no expiration.
"""


@node_router.post(
    "/establish/receive_echo",
    tags=[NodeAPI.NODE_TO_NODE_API.value],
    summary="Receives echo from the `ARCHIVAL_MINER_NODE` for establishment of their connection to the blockchain.",
    description=f"An API endpoint that is only accessile to {UserEntity.MASTER_NODE_USER.name}, where it accepts ECHO request to fetch a certificate before they ({UserEntity.ARCHIVAL_MINER_NODE_USER}) start doing blockchain operations. This will return a certificate as an acknowledgement response from the requestor.",
)
async def acknowledge_as_response(
    x_source: AddressUUID = Header(..., description="The address of the requestor."),
    x_session: JWTToken = Header(
        ..., description="The current session token that the requestor uses."
    ),
    x_acceptance: AuthAcceptanceCode = Header(
        ...,
        description="The auth code that is known as acceptance code, used for extra validation.",
    ),
) -> None:

    db: Any = get_database_instance()  # * Initialized on scope.
    # - [1] Validate such entries from the header.
    # - [1.1] Get the source first.
    fetch_node_source_stmt = select([users.c.unique_address, users.c.email]).where(
        users.c.unique_address == x_source
    )
    validated_source_address = (await db.fetch_all(fetch_node_source_stmt)).pop()

    # - [1.2] Then validate the token by incorporating previous query and the header `x_acceptance`.
    fetch_node_auth_stmt = auth_codes.select().where(
        (auth_codes.c.code == x_acceptance)
        & (
            auth_codes.c.to_email == validated_source_address[1]
        )  # Equivalent to validated_source_address.email.
    )

    validated_auth_code = await db.execute(fetch_node_auth_stmt)

    print("validated_auth_code", validated_auth_code)

    fetch_node_token_stmt = tokens.select().where(
        (tokens.c.token == x_session)
        & (tokens.c.from_user == validated_source_address[0])
    )

    validated_node_token = await db.execute(fetch_node_token_stmt)

    print(
        "validated_node_token",
        validated_node_token,
        dir(validated_node_token),
    )
    # if validate_auth_code and fetch_no


# @node_router.post(
#     "/establish/echo",
#     tags=[NodeAPI.NODE_TO_NODE_API.value],
#     summary="",
#     description="",
#     dependencies=[Depends(EnsureAuthorized(_as=UserEntity.ARCHIVAL_MINER_NODE_USER))],
# )
# async def establish_echo() -> None:
#     """
#     An endpoint that the ARCHIVAL_MINER_NODE_USER will use to provide information to the master node.
#     """
