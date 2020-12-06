function switchStyle() {
    var pics = document.getElementById('pics');
    var txt = document.getElementById('textual');
    if (pics.style.display == 'none') {
        pics.style.display = 'block';
        txt.style.display = 'none';
        document.getElementById('switcher').textContent = 'Lista';

    } else {
        pics.style.display = 'none';
        txt.style.display = 'block';
        document.getElementById('switcher').textContent = 'Kannet';
    }
}

