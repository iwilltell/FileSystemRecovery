# System flow

```mermaid
flowchart TD
    A[Browser Dashboard] --> B[Flask API]
    B --> C[File Manager]
    B --> D[Recovery Manager]
    B --> E[Optimizer]
    C --> F[Disk Manager]
    D --> G[Write-ahead Journal]
    E --> F
    F --> H[Simulated Disk JSON]
```

## Data model

The simulated disk JSON contains:
- `total_blocks`: number of simulated blocks.
- `block_size`: bytes represented by one block.
- `bitmap`: zero for free and one for allocated.
- `files`: path-keyed metadata and file content.
- `directories`: known directory paths.

## Recovery sequence

A pending CREATE record is durably written to the journal before the simulated
operation is applied. The recovery action replays pending records and marks
them COMMITTED. Repeating recovery does not create duplicate files.
