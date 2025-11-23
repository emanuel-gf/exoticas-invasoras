

## 1. Clean the Kml file

With the active environment, run the following
```
python preprocess.py --type manejo --file Manejo1.kml 
```
## Run the db_importer.py

```
python db_importer.py --type ocorrencia --file_name output/processed_data/ocurrencia12_ps.gpkg 
```