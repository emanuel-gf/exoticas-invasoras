

1. There are three big components to run the processor:
- `Xml File` : The file that was exported from the Avenza Maps.
- `schema.json`: Schema refers to how to map the metadata coming from the `kml` file into a defined dtype.
                In fact, `schema.json` is defyning how to map the dtype of each attribute on the metadata. 
- `cleaning_cols`: This is a list being passed inside the main function. It informs which columns should be mutated to split the numbers and         description. The function split by ("-") and retrieve the first value, in case it exists, instead of, return the same input value.


2. Later then, a map dictionary is necessary to map the attribute tables of the Xml file preprocessed.
This map is defying for each column in the DataBase the correspondent column of the geodataframe `gpkg`


## Problems connecting with PostgreSQL

if running in WSL windows:
```
ip route show | grep -i default | awk '{ print $3}'

then use the printed value as the IP address
```

Loop it up, needs to assign at the .config postgres the IP of your local machine. Check if the Postgre is running. 

