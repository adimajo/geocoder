"use strict";

const TILES = document.body.dataset.tileUrl;
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const $ = (id) => document.getElementById(id);
let map = null;

function show(id, visible) {
    $(id).style.display = visible ? "block" : "none";
}

function buildMap(lat, lon, zoom, withMarker) {
    if (map) {
        map.remove();
    }
    map = L.map("map").setView([lat, lon], zoom);
    L.tileLayer(TILES, {attribution: ATTRIBUTION}).addTo(map);
    if (withMarker) {
        L.marker([lat, lon]).addTo(map);
    }
}

function displayError(message) {
    $("error_message").textContent = message;
    show("result_info", false);
    show("result_error", true);
}

function displayResult(row, labels, elapsed) {
    show("result_error", false);
    show("result_info", true);
    $("quality").textContent = row.quality + " : " + (labels[row.quality] || "");
    $("time_ok").textContent = elapsed;
    if (row.lat === null || row.lon === null) {
        buildMap(46.3, 2.92, 6, false);
    } else {
        buildMap(row.lat, row.lon, 17 - row.quality, true);
    }
}

async function geocode() {
    const start = performance.now();
    show("loading", true);
    try {
        const response = await fetch("/geocode_file", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify([{
                address: $("address").value,
                postal_code: $("postal_code").value,
                city: $("city").value,
            }]),
        });
        const body = await response.json();
        if (!response.ok) {
            displayError((body.errors || ["HTTP " + response.status]).join(" "));
            return;
        }
        displayResult(body.data[0], body.quality, Math.round(performance.now() - start));
    } catch (error) {
        displayError(String(error));
    } finally {
        show("loading", false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    buildMap(46.3, 2.92, 6, false);
    $("search").addEventListener("submit", (event) => {
        event.preventDefault();
        geocode();
    });
});
