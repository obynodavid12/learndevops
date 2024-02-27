data=`yq -r '.mysqldatabase.value'  joindemo.yaml | cut -d ' ' -f 2`;
reduced_string=$(cut -c-5 <<< "$data")
id=`yq -e '.mysqlport.value' joindemo.yaml`
reduced_string=$reduced_string-$id

echo "The reduced_string: $reduced_string"
