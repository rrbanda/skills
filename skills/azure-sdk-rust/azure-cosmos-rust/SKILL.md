---
name: azure-cosmos-rust
description: |
  Azure Cosmos DB SDK for Rust (NoSQL API). Use for document CRUD, queries, containers, and globally distributed data.
  Triggers: "cosmos db rust", "CosmosClient rust", "container", "document rust", "NoSQL rust", "partition key".
license: MIT
metadata:
  author: Microsoft
  version: "0.32.0"
  package: azure_data_cosmos
---

# Azure Cosmos DB SDK for Rust

Client library for Azure Cosmos DB NoSQL API — globally distributed, multi-model database.

## Installation

```sh
cargo add azure_data_cosmos azure_identity
```

## Environment Variables

```bash
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_DATABASE=mydb
COSMOS_CONTAINER=mycontainer
```

## Authentication

```rust
use azure_identity::DeveloperToolsCredential;
use azure_data_cosmos::{
    CosmosClient, CosmosAccountReference, CosmosAccountEndpoint, RoutingStrategy,
};

let credential: std::sync::Arc<dyn azure_core::credentials::TokenCredential> =
    DeveloperToolsCredential::new(None)?;
let endpoint: CosmosAccountEndpoint = "https://<account>.documents.azure.com:443/"
    .parse()?;
let account = CosmosAccountReference::with_credential(endpoint, credential);
let client = CosmosClient::builder()
    .build(account, RoutingStrategy::ProximityTo("East US".into()))
    .await?;
```

## Client Hierarchy

| Client            | Purpose                   | Get From                             |
| ----------------- | ------------------------- | ------------------------------------ |
| `CosmosClient`    | Account-level operations  | `CosmosClient::builder().build()`    |
| `DatabaseClient`  | Database operations       | `client.database_client()`           |
| `ContainerClient` | Container/item operations | `database.container_client().await?` |

## Core Workflow

### Get Database and Container Clients

```rust
let database = client.database_client("myDatabase");
let container = database.container_client("myContainer").await?;
```

### Create Item

```rust
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct Item {
    pub id: String,
    pub partition_key: String,
    pub value: String,
}

let item = Item {
    id: "1".into(),
    partition_key: "partition1".into(),
    value: "hello".into(),
};

container.create_item("partition1", item, None).await?;
```

### Read Item

```rust
let response = container.read_item("partition1", "1", None).await?;
let item: Item = response.into_model()?;
```

### Replace Item

```rust
let mut item: Item = container.read_item("partition1", "1", None).await?.into_model()?;
item.value = "updated".into();

container.replace_item("partition1", "1", item, None).await?;
```

### Delete Item

```rust
container.delete_item("partition1", "1", None).await?;
```

## Key Auth (Optional)

Enable key-based authentication with feature flag:

```sh
cargo add azure_data_cosmos --features key_auth
```

## Best Practices

1. **Always specify partition key** — required for point reads and writes
2. **Use `into_model()?`** — to deserialize responses into your types
3. **Derive `Serialize` and `Deserialize`** — for all document types
4. **Use Entra ID auth** — prefer `DeveloperToolsCredential` over key auth
5. **Reuse client instances** — clients are thread-safe and reusable

## Reference Links

| Resource      | Link                                                                               |
| ------------- | ---------------------------------------------------------------------------------- |
| API Reference | https://docs.rs/azure_data_cosmos                                                  |
| Source Code   | https://github.com/Azure/azure-sdk-for-rust/tree/main/sdk/cosmos/azure_data_cosmos |
| crates.io     | https://crates.io/crates/azure_data_cosmos                                         |
