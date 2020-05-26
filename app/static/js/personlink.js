function personlink(name) {
	return '<a href="/person/' + name + '">' + name + '</a>';
}


$(document).ready(function() {
   var editor = false;
   let persons = document.getElementsByClassName('person-list');
   for (i in persons) {
      if (persons[i].innerText !== undefined) {
      if (persons[i].innerText.includes(' (toim.)')) {
          editor = true;
      } else {
          editor = false;
      }
      const spl = persons[i].innerText.replace(' (toim.)', '').split(' & ');
      const output = [];
      for (j in spl) {
         output.push(personlink(spl[j]));
      }
      persons[i].innerHTML = output.join(' & ');
      if (editor == true) { 
          persons[i].innerHTML += ' (toim.)';
      }
    }
   }
});
