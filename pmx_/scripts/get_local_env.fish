function get_local_env
    curl -s "https://api.getpostman.com/environments/$PMX_ENVIRONMENT_ID" \
            --header "X-Api-Key: $POSTMAN_API_KEY" | jq '.environment.values | sort_by(.key)' > $PMX_WORKSPACE_DIR/vars/env.local.json
end

get_local_env
