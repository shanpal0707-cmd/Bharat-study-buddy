# Bharat Study Buddy

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Project Overview and Objectives

Bharat Study Buddy is an innovative educational platform designed to enhance the learning experience for students. The project aims to provide a comprehensive suite of tools that facilitate effective studying, including smart notes, adaptive quizzes, and an AI study planner. The platform also incorporates secure email OTP authentication to ensure user safety and privacy.

## Key Features

- **Smart Notes**: A feature that allows users to create, organize, and manage their study notes efficiently.
- **Adaptive Quiz**: An intelligent quiz system that adapts to the user's learning pace and knowledge level, providing personalized assessments.
- **AI Study Planner**: A tool that leverages artificial intelligence to help users plan their study schedules based on their goals and available time.
- **Email OTP Authentication**: A secure login system that uses One-Time Passwords (OTPs) sent via email for user authentication.

## Technologies and Libraries Used

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Node.js, Express.js (assumed based on common practices)
- **Database**: MongoDB or similar (assumed based on common practices)
- **Authentication**: JSON Web Tokens (JWT) or similar (assumed based on common practices)

## Project Folder Structure

```
Bharat-study-buddy
├── Backend
├── Frontend
│   └── login.html
└── README.md
```

- **Backend**: Contains the server-side code and API endpoints.
- **Frontend**: Contains the client-side code, including HTML, CSS, and JavaScript files.
- **README.md**: Documentation for the project.

## Installation and Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/Bharat-study-buddy.git
   cd Bharat-study-buddy
   ```

2. **Set up the Backend**:
   - Navigate to the `Backend` directory.
   - Install dependencies:
     ```bash
     npm install
     ```
   - Configure environment variables in a `.env` file (see below for details).
   - Start the backend server:
     ```bash
     npm start
     ```

3. **Set up the Frontend**:
   - Navigate to the `Frontend` directory.
   - Open `login.html` in a web browser.

## Environment Variables

To configure the backend, create a `.env` file in the `Backend` directory with the following variables:

```
DATABASE_URL=your_database_url
JWT_SECRET=your_jwt_secret
EMAIL_SERVICE=your_email_service
EMAIL_USER=your_email_user
EMAIL_PASS=your_email_password
```

**Note**: Never share your `.env` file or its contents publicly.

## Commands to Run the Frontend and Backend

- **Run Backend**:
  ```bash
  cd Backend
  npm start
  ```

- **Run Frontend**:
  Open `login.html` in your preferred web browser.

## Screenshots

![Screenshots](link_to_screenshots_placeholder)

## Future Enhancements

- Implement additional features for Smart Notes and Adaptive Quiz.
- Enhance the AI Study Planner with more advanced algorithms.
- Improve user interface and experience based on user feedback.

## Author Information

- **Author**: Your Name
- **GitHub**: [Your GitHub Profile](https://github.com/yourusername)
- **Email**: your.email@example.com

---

This README provides a comprehensive overview of the Bharat Study Buddy project, detailing its objectives, features, technologies used, and setup instructions. For further inquiries or contributions, feel free to reach out!