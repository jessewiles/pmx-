function get_smoke_collection
    curl -s 'https://api.getpostman.com/collections/17705622-e08cfbe9-683c-4b06-b59e-0b4ff82a1144' \
         --header "X-Api-Key: $POSTMAN_API_KEY" | jq > ./scenes/collection.json
end

get_smoke_collection
