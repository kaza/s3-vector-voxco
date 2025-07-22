import streamlit as st
import time
from typing import List, Dict

from utils.embeddings import OpenAIEmbeddings
from utils.similarity import cosine_similarity_percentage
from utils.s3_vectors import S3VectorsManager

# Page configuration
st.set_page_config(
    page_title="S3 Vectors Demo",
    page_icon="🔍",
    layout="wide"
)

# Initialize clients
@st.cache_resource
def init_clients():
    embeddings = OpenAIEmbeddings()
    s3_manager = S3VectorsManager()
    return embeddings, s3_manager

embeddings_client, s3_manager = init_clients()

# Title
st.title("🔍 S3 Vectors Document Search")

# Display document count at the top
doc_count = s3_manager.get_document_count()
st.metric("Total Documents", doc_count)

st.divider()

# Two columns: Add Document and List/Search
col1, col2 = st.columns([1, 2])

# Column 1: Add Document
with col1:
    st.header("➕ Add Document")
    with st.form("add_doc"):
        content = st.text_area("Content", height=150)
        if st.form_submit_button("Add", type="primary", use_container_width=True):
            if content:
                with st.spinner("Adding..."):
                    try:
                        # Time embedding generation
                        start_time = time.time()
                        embedding = embeddings_client.generate_embedding(content)
                        embedding_time = time.time() - start_time
                        
                        result = s3_manager.add_document(content, embedding)
                        st.success(f"✓ Added document {result['id'][:8]}... (embedding: {embedding_time:.2f}s)")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# Column 2: Combined List/Search
with col2:
    st.header("📋 List / Search Documents")
    
    # Search form
    with st.form("list_search"):
        search_query = st.text_input("Search query (leave empty to list all)", placeholder="Optional: Enter search terms...")
        num_results = st.number_input("Number of results", min_value=1, max_value=30, value=10)
        submit = st.form_submit_button("Show Results", type="primary", use_container_width=True)
    
    if submit:
        try:
            if search_query:
                # SEARCH MODE
                st.subheader(f"🔍 Search Results for: '{search_query}'")
                
                with st.spinner("Searching..."):
                    # Time embedding generation
                    embed_start = time.time()
                    query_embedding = embeddings_client.generate_embedding(search_query)
                    embed_time = time.time() - embed_start
                    
                    # Time S3 search
                    search_start = time.time()
                    results = s3_manager.search_documents(query_embedding, top_k=num_results)
                    search_time = time.time() - search_start
                    
                    # Show timing info
                    st.info(f"⏱️ Embedding: {embed_time:.2f}s | Search: {search_time:.2f}s")
                    
                    if results:
                        st.success(f"Found {len(results)} results:")
                        
                        for i, doc in enumerate(results):
                            # Show result with distance
                            distance = doc.get('distance', 'N/A')
                            distance_str = f"{distance:.4f}" if isinstance(distance, (int, float)) else distance
                            
                            # Show more content in the header
                            preview = doc['content'][:100] if len(doc['content']) > 100 else doc['content']
                            
                            with st.expander(f"🔍 {i+1}. (Distance: {distance_str}) {preview}"):
                                st.write("**Document ID:**", doc['key'])
                                st.write("**Full Content:**", doc['content'])
                                st.write("**Distance:**", distance_str)
                                
                                # Delete button
                                if st.button(f"Delete", key=f"del_search_{doc['key']}"):
                                    if s3_manager.delete_document(doc['key']):
                                        st.success("Deleted!")
                                        time.sleep(1)
                                        st.rerun()
                    else:
                        st.warning("No results found!")
                        
                        # Debug info
                        with st.expander("Debug Info"):
                            st.write("Query embedding sample:", query_embedding[:5])
                            
                            # Check what documents exist
                            st.write("\n**Documents in index:**")
                            docs = s3_manager.list_documents(limit=5)
                            st.write(f"Found {len(docs)} documents")
                            for doc in docs:
                                content = doc.get('metadata', {}).get('content', 'N/A')
                                st.write(f"- {content}")
                            
                            # Try a direct test query
                            st.write("\n**Testing with simple vector:**")
                            test_vector = [0.5] * 128
                            test_response = s3_manager.search_documents(test_vector, top_k=3)
                            st.write(f"Test search returned {len(test_response)} results")
            else:
                # LIST MODE
                st.subheader(f"📋 Document List")
                
                docs = s3_manager.list_documents(limit=num_results)
                
                if docs:
                    if len(docs) < num_results:
                        st.warning(f"Requested {num_results} documents, but only {len(docs)} available in index")
                    else:
                        st.info(f"Showing {len(docs)} documents")
                        
                    for i, doc in enumerate(docs):
                        content = doc.get('metadata', {}).get('content', 'N/A')
                        doc_key = doc.get('key', 'Unknown')
                        
                        # Show more content in preview
                        preview = content[:100] if len(content) > 100 else content
                        
                        # Clickable expander for each document
                        with st.expander(f"📄 {i+1}. {preview}"):
                            st.write("**Document ID:**", doc_key)
                            st.write("**Full Content:**", content)
                            
                            # Show embedding preview
                            if 'data' in doc and 'float32' in doc['data']:
                                embedding = doc['data']['float32']
                                st.write(f"**Embedding:** [{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}, ... ] (128 dimensions)")
                            
                            # Delete button
                            if st.button(f"Delete", key=f"del_list_{doc_key}"):
                                if s3_manager.delete_document(doc_key):
                                    st.success("Deleted!")
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.info("No documents found")
                    
        except Exception as e:
            st.error(f"Error: {e}")
            with st.expander("Error Details"):
                st.write(str(e))

# Bottom section: Utilities
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔧 Debug Info")
    if st.button("Show Index Info"):
        try:
            info = s3_manager.get_index_info()
            for key, value in info.items():
                st.write(f"**{key.title()}:** {value}")
            
            # Test query response
            st.write("\n**Testing query_vectors response format:**")
            test_response = s3_manager.test_query_response()
            st.json(test_response)
                
        except Exception as e:
            st.error(f"Error: {e}")

with col2:
    st.subheader("🗑️ Clear All")
    if st.button("Delete All Documents", type="secondary"):
        confirm = st.checkbox("I'm sure I want to delete all documents")
        if confirm and st.button("Confirm Delete All"):
            try:
                deleted_count = s3_manager.delete_all_documents()
                st.success(f"✓ Deleted {deleted_count} documents")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")