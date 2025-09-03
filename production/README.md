# Production Systems

**Owner**: Arden  
**Purpose**: Current deployed versions ready for production use

## Systems

- **v7/**: Sandy's Pipeline (current production, 411s/job)
- **v14/**: Complete System (ready for deployment, 29.1s/job)

## Usage

```bash
# Run current production
cd v7 && python main.py

# Run next-gen production
cd v14 && python reports.py
```

## Deployment

Each version is self-contained with its own:
- Configuration files
- Data directories  
- Output directories
- Python cache

See individual version directories for specific instructions.
