function get_smoke_collection
    curl -s 'https://api.getpostman.com/collections/5319611-1b64b494-ab13-4d7e-a865-0713b673f646' \
         --header "X-Api-Key: $POSTMAN_API_KEY" | jq > ./scenes/collection.json
end

get_smoke_collection
