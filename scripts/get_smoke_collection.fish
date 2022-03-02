function get_smoke_collection
    curl -s "https://api.getpostman.com/collections/$PMX_COLLECTION_ID" \
         --header "X-Api-Key: $POSTMAN_API_KEY" | jq > $PMX_WORKSPACE_DIR/collection.json
end

get_smoke_collection
