function update_pubseries() {
	var name = document.getElementById('publisher').value;
	var request = $.ajax({
		type: 'GET',
		url: '/list_pubseries/' + name + '/',
	});
	request.done(function(data){
		var option_list = [[""]].concat(data);
		
		$("#pubseries").empty();
		for (var i = 0; i < option_list.length; i++) {
			$("#pubseries").append(
				$("<option></option>").attr(
					"value", option_list[i][0]).text(option_list[i][1])
				);
		}
	});
});
