document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchDoctorsForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            searchDoctors();
        });
    }

    const addDoctorForm = document.getElementById('addDoctorForm');
    if (addDoctorForm) {
        addDoctorForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addDoctor();
        });
    }

    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

function searchDoctors() {
    const specialization = document.getElementById('specialization').value;
    const date = document.getElementById('appointmentDate').value;
    const resultsDiv = document.getElementById('doctorResults');
    
    resultsDiv.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    
    fetch(`/search_doctors?specialization=${specialization}&date=${date}`)
        .then(response => response.json())
        .then(doctors => {
            displayDoctors(doctors);
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = '<div class="alert alert-danger">Error searching doctors</div>';
        });
}

function displayDoctors(doctors) {
    const resultsDiv = document.getElementById('doctorResults');
    if (doctors.length === 0) {
        resultsDiv.innerHTML = '<div class="alert alert-info">No doctors found matching your criteria.</div>';
        return;
    }

    let html = '<div class="row">';
    doctors.forEach(doctor => {
        html += `
            <div class="col-md-6 mb-3">
                <div class="card appointment-card">
                    <div class="card-body">
                        <h5 class="card-title">Dr. ${doctor.name}</h5>
                        <p class="card-text">
                            <strong>Specialization:</strong> ${doctor.specialization}<br>
                            <strong>Department:</strong> ${doctor.department}<br>
                            <strong>Experience:</strong> ${doctor.experience || 'N/A'} years<br>
                            <strong>Fee:</strong> $${doctor.consultation_fee || '0'}
                        </p>
                        <button class="btn btn-primary btn-sm" onclick="showBookingModal(${doctor.id}, '${doctor.name}')">
                            Book Appointment
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    resultsDiv.innerHTML = html;
}

function showBookingModal(doctorId, doctorName) {
    const modal = new bootstrap.Modal(document.getElementById('bookingModal'));
    document.getElementById('bookingDoctorId').value = doctorId;
    document.getElementById('bookingDoctorName').textContent = doctorName;
    modal.show();
}

function bookAppointment() {
    const doctorId = document.getElementById('bookingDoctorId').value;
    const date = document.getElementById('bookingDate').value;
    const time = document.getElementById('bookingTime').value;
    const symptoms = document.getElementById('symptoms').value;
    
    if (!date || !time) {
        alert('Please select date and time');
        return;
    }
    
    const formData = new FormData();
    formData.append('doctor_id', doctorId);
    formData.append('date', date);
    formData.append('time', time);
    formData.append('symptoms', symptoms);
    
    fetch('/book_appointment', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('bookingModal')).hide();
            location.reload();
        } else {
            alert(data.error || 'Error booking appointment');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error booking appointment');
    });
}

function addDoctor() {
    const form = document.getElementById('addDoctorForm');
    const formData = new FormData(form);
    
    fetch('/admin/add_doctor', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            form.reset();
            location.reload();
        } else {
            alert(data.error || 'Error adding doctor');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error adding doctor');
    });
}