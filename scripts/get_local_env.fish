function get_local_env
    curl -s 'https://api.getpostman.com/environments/17705622-2abed1bf-2c5a-4764-a9df-74abf3cfa5ca' \
            --header "X-Api-Key: $POSTMAN_API_KEY" | jq '.environment.values | sort_by(.key)' > ./scenes/vars/env.local.json
end

get_local_env