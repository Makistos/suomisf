function personlink(name) {
	return '<a href="/person/' + name + '">' + name + '</a>';
}


$(document).ready(function() {
   let persons = document.getElementsByClassName('person-list');
   for (i in persons) {
      const spl = persons[i].innerText.split(' & ');
      const output = [];
      for (j in spl) {
         output.push(personlink(spl[j]));
      }
      persons[i].innerHTML = output.join(' & ');
   }
});
