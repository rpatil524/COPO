//scripts takes a profile id (id) and retrieves profile components (listed in components array)

var id = "xxxx" //substitute this with a valid profile id

var components = ["PublicationCollection", "PersonCollection", "SampleCollection", "SubmissionCollection", "SourceCollection", "DataFileCollection"]

printjson('***********************Profile*********************************')
db.Profiles.find({
    "_id": ObjectId(id)
}).forEach(
    function(file) {
        printjson(file);
    }
);

components.forEach(function(component) {
    print("*********************************" + component + "*********************************")
    var indx = 0
    db.getCollection(component).find({
        "profile_id": id
    }).forEach(function(file) {
    	if(indx > 0) {
    		print(',')
    	}

    	++indx

        printjson(file);
    });

});