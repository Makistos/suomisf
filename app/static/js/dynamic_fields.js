  <script>
    $(function () {
      $("div[data-toggle=fieldset]").each(function () {
        var $this = $(this);
        // Add entry
        $this.find("button[data-toggle=fieldset-add-row]").click(function () {
          var target = $($(this).data("target"));
          console.log("target");
          console.log(target);
          var oldrow = target.find("[data-toggle=fieldset-entry]:last");
          var row = oldrow.clone(true, true);
          var elem_id = row.find(":input")[0].id;
          var elem_num = parseInt(elem_id.replace(/.*-(\d{1,4})-.*/m, '$1')) + 1;
          row.attr('data-id', elem_num);
          row.find(":input").each(function () {
            console.log(this);
            var id = $(this).attr('id').replace('-' + (elem_num - 1) + '-', '-' + (elem_num) + '-');
            $(this).attr('name', id).attr('id', id).val('').removeAttr("checked");
          });
          oldrow.after(row);
        });
        // Remove entry
        $this.find("button[data-toggle=fieldset-remove-row]").click(function () {
          if ($this.find("[data-toggle=fieldset-entry]").length > 1) {
            var thisRow = $(this).closest("[data-toggle=fieldset-entry]");
            thisRow.remove();
          }
        });
      });
    });
  </script>
