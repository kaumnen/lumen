from ..vector_store.qdrant_manager import setup_qdrant_client


def get_collection_metadata():
    qdrant_client, collection_name = setup_qdrant_client()

    collection_metadata = qdrant_client.get_collection(collection_name)

    vector_count = collection_metadata.points_count
    collection_status = collection_metadata.status
    optimizer_status = collection_metadata.optimizer_status

    return vector_count, collection_status, optimizer_status
