COPY (
  SELECT
    id,
    client_id,
    user_id,
    access_token,
    refresh_token,
    expires,
    _scopes,
    token_type,
    is_personal,
    is_internal
  FROM
    oauth2server_token
) TO STDOUT WITH (FORMAT binary);
