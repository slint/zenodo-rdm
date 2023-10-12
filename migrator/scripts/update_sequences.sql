SELECT setval(pg_get_serial_sequence('access_actionssystemroles', 'id'), COALESCE(max(id) + 1, 1), false) FROM access_actionssystemroles;
SELECT setval(pg_get_serial_sequence('accounts_user', 'id'), COALESCE(max(id) + 1, 1), false) FROM accounts_user;
SELECT setval(pg_get_serial_sequence('banners', 'id'), COALESCE(max(id) + 1, 1), false) FROM banners;
SELECT setval(pg_get_serial_sequence('files_location', 'id'), COALESCE(max(id) + 1, 1), false) FROM files_location;
SELECT setval(pg_get_serial_sequence('oaiserver_set', 'id'), COALESCE(max(id) + 1, 1), false) FROM oaiserver_set;
SELECT setval(pg_get_serial_sequence('pages_page', 'id'), COALESCE(max(id) + 1, 1), false) FROM pages_page;
SELECT setval(pg_get_serial_sequence('pidstore_pid', 'id'), COALESCE(max(id) + 1, 1), false) FROM pidstore_pid;
SELECT setval(pg_get_serial_sequence('request_number_seq', 'value'), COALESCE(max(value) + 1, 1), false) FROM request_number_seq;
SELECT setval(pg_get_serial_sequence('access_actionsroles', 'id'), COALESCE(max(id) + 1, 1), false) FROM access_actionsroles;
SELECT setval(pg_get_serial_sequence('access_actionsusers', 'id'), COALESCE(max(id) + 1, 1), false) FROM access_actionsusers;
SELECT setval(pg_get_serial_sequence('oauthclient_remoteaccount', 'id'), COALESCE(max(id) + 1, 1), false) FROM oauthclient_remoteaccount;
SELECT setval(pg_get_serial_sequence('pages_pagelist', 'id'), COALESCE(max(id) + 1, 1), false) FROM pages_pagelist;
SELECT setval(pg_get_serial_sequence('oauth2server_token', 'id'), COALESCE(max(id) + 1, 1), false) FROM oauth2server_token;
SELECT setval(pg_get_serial_sequence('communities_featured', 'id'), COALESCE(max(id) + 1, 1), false) FROM communities_featured;

-- Explicit highger values for tracking pre/post-migration objects
SELECT setval(pg_get_serial_sequence('pidstore_recid', 'recid'), 10000000, false);
SELECT setval(pg_get_serial_sequence('accounts_user', 'id'), 1000000, false);
