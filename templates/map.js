function initMap() {
    var map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: YOUR_DEFAULT_LATITUDE, lng: YOUR_DEFAULT_LONGITUDE },
        zoom: 8
    });

    // Loop through weather_data and add markers
    {% for entry in weather_data %}
    var marker{{ loop.index }} = new google.maps.Marker({
        position: { lat: {{ entry.latitude }}, lng: {{ entry.longitude }} },
        map: map,
        title: "{{ entry.location }}"
    });
    {% endfor %}
}
