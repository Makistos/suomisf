        $(".ownerstate").click(function() {
            console.log("beep");
		var obj = $('#SelectElementId');
            if ($(this).attr('href') == '#remove') {
		$(this).parent().attr('style', 'padding-left: 25px;');
                $(this).attr('href', '#add');
                $(this).text(' + ');
                var request = $.ajax({
                    type: 'POST',
                    url: '/remove_from_owned/' + $(this).attr('id'),
                });
            } else {
		$(this).parent().attr('style', 'border-left: 6px solid grey; padding-left: 19px');
		$(this).attr('href', '#remove');
		$(this).text(' - ');
                var request = $.ajax({
                    type: 'POST',
                    url: '/add_to_owned/' + $(this).attr('id'),
                });
	    }
           return false;
        });
