	var loading = {};
	var csrf_token = "{{csrf_token}}";

	$(document).ready(function() {
		$('select').each(function() {
			loading[$(this).data('name')] = true;
			if ($(this).data('width')) {
				this_width = $(this).data('width')
			} else {
				this_width = 'resolve';
			}
			$(this).select2({
				ajax: { 
					url: $(this).data('search'),
					dataType: 'json',
					delay: 250,
					data: function(params) {
						return {
							q: params.term,
						};
					},
				},
				minimumInputLength: 3,
				placeholder: $(this).data('placeholder'),
				tags: Boolean($(this).data('tags')),
				tokenSeparators: [',', ', '],
				width: this_width,
				createTag: function(params) {
					var term = $.trim(params.term);
					var id = 0;
					if (term === '') {
						return null;
					}
					return {
						id: id,
						text: term,
						newTag: true
					}
				},
			}),
			/* Fill selectors with data from db. */
			$.ajax({
				type: "GET",
				url: $(this).data('init') + '/' + itemId
			}).then(data => {
				fill_options($(this), data);
				loading[$(this).data('name')] = false;
			});

			// Callbacks that save changes to the select2 fields to db.
			$(this).on("select2:select", function(evt) {
				if (!loading[$(this).data('name')]) {
					saveSelector($(this), $(this).data('save'), $(this).select2('data'));
					var args = JSON.stringify(evt.params, function (key, value) {
						if (value && value.nodeName) return "[DOM node]";
						if (value instanceof $.Event) return "[$.Event]";
						return value;
					});
						console.log("select: " + args);
						console.log("select: " + evt.params['data']['id']);
				}
			}),
			$(this).on("select2:unselect", function(evt) {
				if (!loading[$(this).data('name')]) {
					saveSelector($(this), $(this).data('save'), $(this).select2('data'));
					var args = JSON.stringify(evt.params, function (key, value) {
						if (value && value.nodeName) return "[DOM node]";
						if (value instanceof $.Event) return "[$.Event]";
						return value;
					});
						console.log("unselect: " + args);
						console.log("unselect: " + evt.params['data']['id']);
				}
			})
		})
		
		// Fill existing values to select2 fields
		function fill_options(selector, data) {
			var people = JSON.parse(data);
			for (var i = 0; i < people.length; i++) {
				var person = people[i];
				var id = Number(person['id']);
				var name = person['text'];
				var option = new Option(name, id, true, true);
				selector.append(option).trigger('change');
			}
			selector.trigger({
				type: 'select2:select',
				params: {
					data: data
				}
			});
		}

		// edit_form is the checkbox that admin can click to edit the fields
		$('#edit_form').removeAttr('checked');

		$('#edit_form').on('change', function() {
			var view_elements = document.getElementsByClassName('view-field');
			var edit_elements = document.getElementsByClassName('edit-field');
			var input_field = document.getElementById('edit_form');
			for (var i = 0; i < view_elements.length; i++) {
				if (input_field.checked) {
					//edit_elements.setAttribute('disabled', false);
					view_elements[i].style.display = "none";
					edit_elements[i].style.display = "block";
				} else {
					location.reload();
					//edit_elements.setAttribute('disabled', false);
					view_elements[i].style.display = "block";
					edit_elements[i].style.display = "none";
				}
			}
		});
		// Hide edit elements by default
		var elements_to_hide = document.getElementsByClassName('edit-field');

		for (var i = 0; i < elements_to_hide.length; i++) {
			elements_to_hide[i].style.display = "none";
		}
	});
		function saveSelector(target, endpoint, item_list) {
			if (loading === true) {
				return false;
			}
			const items = item_list.map(item => ({"id": item.id, "text": item.text}));
			$.ajax({
				url: endpoint,
				type: "POST",
				dataType: "json",
				data: { items: JSON.stringify(items), 
					    itemId: JSON.stringify(itemId)} 
			});

		}

		function send_form(form, form_id, url, type, inner_ajax, formData) {
			if (form[0].checkValidity() && isFormDataEmpty(formData) == false) {
				event.preventDefault();
				inner_ajax(url, type, formData);
			} else {
				var labels = document.getElementsByTagName('LABEL');
				for (var i=0; i < labels.length; i++) {
					if (labels[i].htmlFor != '') {
						var elem = document.getElementById(labels[i].htmlFor);
						if (elem) {
							elem.label = labels[i];
						}
					}
				}
				/*var Form = document.getElementById(form_id);
				var invalidList = Form.querySelectorAll(':invalid:');

				if (typeof invalidList !== 'undefined' && invalidList.length > 0) {
					for (var item of invalidList) {
						M.toast({html: "Ole hyvä ja täytä kenttä " + item.label.innerHTML+"", classes: 'bg-danger text-white'});
					} 
				} else {
					M.toast({html: 'Virhe. Yritä uudelleen.', classes: 'bg-danger text-white'});
				}*/
			}
		}
		function isFormDataEmpty(formData) {
			for (var [key, value] of formData.entries()) {
				if (key != 'csrf_token') {
					if (value != '' && value != []) {
						return false;
					}
				}
			}
			return true;
		}

		function modular_ajax(url, type, formData) {
			$.ajax({
				url: url,
				type: type,
				data: formData,
				processData: false,
				contentType: false,
				success: function(data){
					if (!$.trim(data.feedback)) {
						toast_error_msg = "Tyhjä paluuarvo.";
						toast_category = "danger";
					} else {
						toast_error_msg = data.feedback;
						toast_category = data.category;
					}
				},
				error: function(xhr) {
					console.log("Virhe. Tarkista tiedot alta.");
					console.log(xhr.status + ": " + xhr.responseText);
					toast_error_msg = "Virhe";
					toast_category = "danger";
				}
			}).done(function() {
				M.toast({html: toast_error_msg, classes: 'bg-' + toast_category + ' text-white'});
			})
		}

		// $.ajaxSetup({
		function saveArticleForm() {
			var form = $('#articleForm');
			var form_id = 'articleForm';
			var url = form.prop('action');
			var type = form.prop('method');
			var formData = getArticleFormData(form_id);

			send_form(form, form_id, url, type, modular_ajax, formData);
		}
		function getArticleFormData(form) {
			var formData = new FormData(document.getElementById(form));
			return formData;
		}
