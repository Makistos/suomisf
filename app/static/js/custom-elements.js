class PersonName extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        if (this.getAttribute('print') == '1') {
            var name = this.getAttribute('name');
        } else {
            var name = '<a href="/person/' 
                + this.getAttribute('id') 
                + '">'
                + this.getAttribute('name')
                + '</a>';
        }
        this.innerHTML = 
            '<h3>' 
            + name
            + '</h3>';
    }
}

customElements.define('person-name', PersonName);
