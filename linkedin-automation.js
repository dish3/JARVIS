/**
 * LinkedIn Automation Module for JARVIS
 * Handles posting, scheduling, and managing LinkedIn content
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

class LinkedInAutomation {
  constructor(email, password) {
    this.email = email;
    this.password = password;
    this.browser = null;
    this.page = null;
    this.isLoggedIn = false;
  }

  /**
   * Initialize browser and login to LinkedIn
   */
  async initialize() {
    try {
      console.log("[LinkedIn] Launching browser...");
      this.browser = await puppeteer.launch({
        headless: false, // Show browser for user to see what's happening
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      this.page = await this.browser.newPage();
      await this.page.setViewport({ width: 1280, height: 720 });

      console.log("[LinkedIn] Navigating to LinkedIn...");
      await this.page.goto('https://www.linkedin.com/login', { waitUntil: 'networkidle2' });

      // Login
      await this.login();
      this.isLoggedIn = true;
      console.log("[LinkedIn] ✅ Successfully logged in!");
      return { success: true, message: "LinkedIn login successful" };
    } catch (err) {
      console.error("[LinkedIn] Initialization error:", err);
      return { success: false, error: err.message };
    }
  }

  /**
   * Login to LinkedIn
   */
  async login() {
    try {
      // Enter email
      await this.page.type('input[name="session_key"]', this.email, { delay: 50 });
      
      // Enter password
      await this.page.type('input[name="session_password"]', this.password, { delay: 50 });
      
      // Click login button
      await this.page.click('button[type="submit"]');
      
      // Wait for navigation
      await this.page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 });
      
      console.log("[LinkedIn] Login completed");
    } catch (err) {
      throw new Error(`LinkedIn login failed: ${err.message}`);
    }
  }

  /**
   * Create and post content to LinkedIn
   * @param {string} content - The post content/text
   * @param {string} imageUrl - Optional image URL to attach
   * @param {boolean} schedule - Whether to schedule the post
   * @param {string} scheduleTime - ISO timestamp for scheduled posting
   */
  async createPost(content, imageUrl = null, schedule = false, scheduleTime = null) {
    try {
      if (!this.isLoggedIn) {
        throw new Error("Not logged in to LinkedIn");
      }

      console.log("[LinkedIn] Creating post...");

      // Navigate to home feed
      await this.page.goto('https://www.linkedin.com/feed/', { waitUntil: 'networkidle2' });

      // Click on "Start a post" button
      const startPostBtn = await this.page.$('button:has-text("Start a post")');
      if (!startPostBtn) {
        // Try alternative selector
        await this.page.click('div[role="button"]:has-text("Start a post")');
      } else {
        await startPostBtn.click();
      }

      // Wait for post modal to appear
      await this.page.waitForSelector('div[role="dialog"]', { timeout: 5000 });
      console.log("[LinkedIn] Post modal opened");

      // Click on text area and type content
      await this.page.click('div[contenteditable="true"]');
      await this.page.type('div[contenteditable="true"]', content, { delay: 30 });
      console.log("[LinkedIn] Content typed");

      // Add image if provided
      if (imageUrl) {
        await this.addImageToPost(imageUrl);
      }

      // Post or Schedule
      if (schedule && scheduleTime) {
        await this.schedulePost(scheduleTime);
      } else {
        await this.publishPost();
      }

      return { success: true, message: "Post created successfully" };
    } catch (err) {
      console.error("[LinkedIn] Post creation error:", err);
      return { success: false, error: err.message };
    }
  }

  /**
   * Add image to LinkedIn post
   */
  async addImageToPost(imageUrl) {
    try {
      console.log("[LinkedIn] Adding image to post...");

      // Find and click the image upload button
      const uploadBtn = await this.page.$('button[aria-label*="image"]');
      if (uploadBtn) {
        await uploadBtn.click();
      }

      // Handle file upload
      const inputUploadHandle = await this.page.$('input[type="file"]');
      if (inputUploadHandle) {
        // If it's a local file path
        if (fs.existsSync(imageUrl)) {
          await inputUploadHandle.uploadFile(imageUrl);
        } else {
          // If it's a URL, download and save temporarily
          const tempImagePath = await this.downloadImage(imageUrl);
          await inputUploadHandle.uploadFile(tempImagePath);
        }
      }

      // Wait for image to upload
      await this.page.waitForTimeout(2000);
      console.log("[LinkedIn] Image added");
    } catch (err) {
      console.warn("[LinkedIn] Image upload failed:", err.message);
      // Continue without image
    }
  }

  /**
   * Download image from URL to temporary location
   */
  async downloadImage(imageUrl) {
    try {
      const https = require('https');
      const tempPath = path.join(require('os').tmpdir(), `linkedin_img_${Date.now()}.jpg`);
      
      return new Promise((resolve, reject) => {
        https.get(imageUrl, (response) => {
          const fileStream = fs.createWriteStream(tempPath);
          response.pipe(fileStream);
          fileStream.on('finish', () => {
            fileStream.close();
            resolve(tempPath);
          });
        }).on('error', reject);
      });
    } catch (err) {
      throw new Error(`Image download failed: ${err.message}`);
    }
  }

  /**
   * Publish the post immediately
   */
  async publishPost() {
    try {
      console.log("[LinkedIn] Publishing post...");

      // Find and click the "Post" button
      const postBtn = await this.page.$('button:has-text("Post")');
      if (postBtn) {
        await postBtn.click();
      } else {
        // Try alternative selector
        await this.page.click('button[aria-label="Post"]');
      }

      // Wait for post to be published
      await this.page.waitForTimeout(3000);
      console.log("[LinkedIn] ✅ Post published!");
    } catch (err) {
      throw new Error(`Post publishing failed: ${err.message}`);
    }
  }

  /**
   * Schedule post for later
   */
  async schedulePost(scheduleTime) {
    try {
      console.log("[LinkedIn] Scheduling post...");

      // Click on schedule button (if available)
      const scheduleBtn = await this.page.$('button:has-text("Schedule")');
      if (scheduleBtn) {
        await scheduleBtn.click();
      }

      // Set date and time
      const date = new Date(scheduleTime);
      const dateStr = date.toLocaleDateString();
      const timeStr = date.toLocaleTimeString();

      // Fill in date field
      const dateInput = await this.page.$('input[type="date"]');
      if (dateInput) {
        await dateInput.type(dateStr);
      }

      // Fill in time field
      const timeInput = await this.page.$('input[type="time"]');
      if (timeInput) {
        await timeInput.type(timeStr);
      }

      // Click schedule button
      await this.page.click('button:has-text("Schedule")');
      await this.page.waitForTimeout(2000);

      console.log("[LinkedIn] ✅ Post scheduled for", scheduleTime);
    } catch (err) {
      throw new Error(`Post scheduling failed: ${err.message}`);
    }
  }

  /**
   * Generate content using AI (to be called from main.js with Groq/Gemini)
   */
  static async generateContent(topic, tone = "professional", length = "medium") {
    // This will be called from main.js with AI integration
    // Returns a promise that resolves with generated content
    return `Generated LinkedIn post about ${topic} in ${tone} tone`;
  }

  /**
   * Close browser and cleanup
   */
  async close() {
    try {
      if (this.browser) {
        await this.browser.close();
        console.log("[LinkedIn] Browser closed");
      }
    } catch (err) {
      console.error("[LinkedIn] Error closing browser:", err);
    }
  }
}

module.exports = LinkedInAutomation;
