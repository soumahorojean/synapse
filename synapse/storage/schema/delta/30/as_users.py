# Copyright 2016 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from synapse.storage.appservice import ApplicationServiceStore


logger = logging.getLogger(__name__)


def run_upgrade(cur, database_engine, config, *args, **kwargs):
    # NULL indicates user was not registered by an appservice.
    try:
        cur.execute("ALTER TABLE users ADD COLUMN appservice_id TEXT")
    except:
        # Maybe we already added the column? Hope so...
        pass

    cur.execute("SELECT name FROM users")
    rows = cur.fetchall()

    config_files = []
    try:
        config_files = config.app_service_config_files
    except AttributeError:
        logger.warning("Could not get app_service_config_files from config")
        pass

    appservices = ApplicationServiceStore.load_appservices(
        config.server_name, config_files
    )

    owned = {}

    for row in rows:
        user_id = row[0]
        for appservice in appservices:
            if appservice.is_exclusive_user(user_id):
                if user_id in owned.keys():
                    logger.error(
                        "user_id %s was owned by more than one application"
                        " service (IDs %s and %s); assigning arbitrarily to %s" %
                        (user_id, owned[user_id], appservice.id, owned[user_id])
                    )
                owned[user_id] = appservice.id

    for user_id, as_id in owned.items():
        cur.execute(
            database_engine.convert_param_style(
                "UPDATE users SET appservice_id = ? WHERE name = ?"
            ),
            (as_id, user_id)
        )