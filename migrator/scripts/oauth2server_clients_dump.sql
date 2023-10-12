COPY (
  SELECT
    name,
    client_id,
    description,
    website,
    user_id,
    client_secret,
    _redirect_uris,
    _default_scopes,
    is_internal,
    is_confidential
  FROM
    oauth2server_client
) TO STDOUT WITH (FORMAT binary);
