var loading = {};

$(document).ready(function () {
  // edit_form is the checkbox that admin can click to edit the fields
  $("#edit_form").removeAttr("checked");

  $("select").each(function () {
    loading[$(this).data("name")] = true;
    if ($(this).data("width")) {
      this_width = $(this).data("width");
    } else {
      this_width = "resolve";
    }
    if ($(this).data("mininput")) {
      minInputLen = $(this).data("mininput");
    } else {
      minInputLen = 3;
    }
    $(this).select2({
      ajax: {
        url: $(this).data("search"),
        dataType: "json",
        delay: 250,
        data: function (params) {
          return {
            q: params.term,
          };
        },
      },
      minimumInputLength: minInputLen,
      placeholder: $(this).data("placeholder"),
      tags: Boolean($(this).data("tags")),
      tokenSeparators: [",", ", "],
      width: this_width /*,
      createTag: function (params) {
        var term = $.trim(params.term);
        var id = 0;
        if (term === "") {
          return null;
        }
        return {
          id: id,
          text: term,
          newTag: true,
        };
      },*/,
    }),
      /* Fill selectors with data from db. */
      $.ajax({
        type: "GET",
        url: $(this).data("init") + "/" + itemId,
      }).then((data) => {
        fill_options($(this), data);
        loading[$(this).data("name")] = false;
      });

    // Callbacks that save changes to the select2 fields to db.
    $(this).on("select2:select", function (evt) {
      if (!loading[$(this).data("name")]) {
        saveSelector($(this), $(this).data("save"), $(this).select2("data"));
        var args = JSON.stringify(evt.params, function (key, value) {
          if (value && value.nodeName) return "[DOM node]";
          if (value instanceof $.Event) return "[$.Event]";
          return value;
        });
        console.log("selecting: " + evt.params["data"]["id"]);
      }
    }),
      $(this).on("select2:unselect", function (evt) {
        if (!loading[$(this).data("name")]) {
          saveSelector($(this), $(this).data("save"), $(this).select2("data"));
          var args = JSON.stringify(evt.params, function (key, value) {
            if (value && value.nodeName) return "[DOM node]";
            if (value instanceof $.Event) return "[$.Event]";
            return value;
          });
          console.log("unselecting: " + evt.params["data"]["id"]);
        }
      });
  });

  // Fill existing values to select2 fields
  function fill_options(selector, data) {
    console.log("selector " + selector.data("name") + ": " + data);
    var items = JSON.parse(data);
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var id = Number(item["id"]);
      var name = item["text"];
      var option = new Option(name, id, true, true);
      selector.append(option).trigger("change");
    }
    selector.trigger({
      type: "select2:select",
      params: {
        data: data,
      },
    });
  }

  $("#edit_form").on("change", function () {
    var view_elements = document.getElementsByClassName("view-field");
    var edit_elements = document.getElementsByClassName("edit-field");
    var input_field = document.getElementById("edit_form");
    for (var i = 0; i < view_elements.length; i++) {
      if (input_field.checked) {
        view_elements[i].style.display = "none";
      } else {
        view_elements[i].style.display = "block";
      }
    }
    for (var i = 0; i < edit_elements.length; i++) {
      if (input_field.checked) {
        edit_elements[i].style.display = "block";
      } else {
        edit_elements[i].style.display = "none";
      }
      if (!input_field.checked) {
        var itemForm = document.getElementById("itemForm");
        itemForm.submit();
      }
    }
  });

  $("#image_upload").on("change", function () {
    formdata = new FormData();
    var file = this.files[0];
    if (formdata) {
      formdata.append("image", file);
      formdata.append("id", itemId);
      $.ajax({
        url: $(this).data("save"),
        type: "POST",
        data: formdata,
        processData: false,
        contentType: false,
        success: function () {},
      });
    }
  });
  // Hide edit elements by default
  var elements_to_hide = document.getElementsByClassName("edit-field");

  for (var i = 0; i < elements_to_hide.length; i++) {
    elements_to_hide[i].style.display = "none";
  }

  $(".form-item").each(function () {
    console.log("id: " + this.id);
    //$(this).onblur = saveForm(this);
    this.addEventListener("blur", function () {
      //saveForm(this);
      // var form = document.getElementById("itemForm");
      //console.log("submitting");
      //this.form.submit();
    });
  });
});
function saveSelector(target, endpoint, item_list) {
  if (loading === true) {
    return false;
  }
  const items = item_list.map((item) => ({ id: item.id, text: item.text }));
  console.log(endpoint);
  console.log(items);
  $.ajax({
    url: endpoint,
    type: "POST",
    dataType: "json",
    data: {
      items: JSON.stringify(items),
      itemId: JSON.stringify(itemId),
    },
  });
}

/*
function send_form(form, form_id, url, type, inner_ajax, formData) {
  if (form[0].checkValidity() && isFormDataEmpty(formData) == false) {
    event.preventDefault();
    inner_ajax(url, type, formData);
  } else {
    var labels = document.getElementsByTagName("LABEL");
    for (var i = 0; i < labels.length; i++) {
      if (labels[i].htmlFor != "") {
        var elem = document.getElementById(labels[i].htmlFor);
        if (elem) {
          elem.label = labels[i];
        }
      }
    }
  */
/*var Form = document.getElementById(form_id);
		var invalidList = Form.querySelectorAll(':invalid:');

		if (typeof invalidList !== 'undefined' && invalidList.length > 0) {
			for (var item of invalidList) {
				M.toast({html: "Ole hyvä ja täytä kenttä " + item.label.innerHTML+"", classes: 'bg-danger text-white'});
			}
		} else {
			M.toast({html: 'Virhe. Yritä uudelleen.', classes: 'bg-danger text-white'});
    }*/
/*
  }
}
*/
/*
function isFormDataEmpty(formData) {
  for (var [key, value] of formData.entries()) {
    if (key != "csrf_token") {
      if (value != "" && value != []) {
        return false;
      }
    }
  }
  return true;
}
$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (
      !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) &&
      !this.crossDomain
    ) {
      xhr.setRequestHeader("X-CSRFToken", csrf_token);
    }
  },
});

function modular_ajax(url, type, formData) {
  $.ajax({
    url: url,
    type: type,
    data: formData,
    processData: false,
    contentType: false,
    success: function (data) {
      if (!$.trim(data.feedback)) {
        toast_error_msg = "Tyhjä paluuarvo.";
        toast_category = "danger";
      } else {
        toast_error_msg = data.feedback;
        toast_category = data.category;
      }
    },
    error: function (xhr) {
      console.log("Virhe. Tarkista tiedot alta.");
      console.log(xhr.status + ": " + xhr.responseText);
      toast_error_msg = "Virhe";
      toast_category = "danger";
    },
  }).done(function () {
    // M.toast({
    //   html: toast_error_msg,
    //   classes: "bg-" + toast_category + " text-white",
    //});
  });
}
*/
// $.ajaxSetup({
/*
function saveForm(element) {
  console.log("sending form for " + element.id);

  var input_field = document.getElementById("edit_form");
  if (input_field.checked) {
    var form = document.getElementById("itemForm");
    var form_id = form.id;
    var url = form.action + "/" + itemId;
    //var url = "";
    var type = form.method;
    var formData = getFormData(form);

    send_form(form, form_id, url, type, modular_ajax, formData);
  }
}
function getFormData(form) {
  var formData = new FormData(form);

  for (let i = 0; i < form.elements.length; i++) {
    const elem = form.elements[i];
    if (elem.id != "") {
      formData[elem.name] = elem.value;
    }
  }

  return formData;
}
*/
