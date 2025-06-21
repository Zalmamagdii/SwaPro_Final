const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();

// Middleware
app.use(cors({
  origin: '*', // Allow all origins
  credentials: true
}));
app.use(bodyParser.json({ limit: '50mb' })); // Increase payload limit for large images

// MongoDB Atlas Connection
const MONGODB_URI = 'mongodb+srv://salma:XzXz5pvh@cluster0.006lsbb.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0';

mongoose.connect(MONGODB_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true
})
.then(() => {
  console.log('Connected to MongoDB Atlas');
  // Verify connection by checking if we can access the database
  mongoose.connection.db.admin().listDatabases()
    .then(result => {
      console.log('Available databases:', result.databases.map(db => db.name));
    })
    .catch(err => console.error('Error listing databases:', err));
})
.catch(err => {
  console.error('MongoDB connection error:', err);
  process.exit(1); // Exit if we can't connect to the database
});

// Add connection error handler
mongoose.connection.on('error', err => {
  console.error('MongoDB connection error:', err);
});

// Add connection success handler
mongoose.connection.once('open', () => {
  console.log('MongoDB connection established successfully');
});

// User Schema
const userSchema = new mongoose.Schema({
  username: { type: String, required: true, unique: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true }
});

const User = mongoose.model('User', userSchema);

// Routes
app.post('/signup', async (req, res) => {
  try {
    console.log('Received signup request:', req.body);
    const { username, email, password } = req.body;

    // Check if user already exists
    const existingUser = await User.findOne({ $or: [{ email }, { username }] });
    if (existingUser) {
      console.log('User already exists:', existingUser);
      return res.status(400).json({ message: 'User already exists' });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Create new user
    const user = new User({
      username,
      email,
      password: hashedPassword
    });

    console.log('Saving new user:', { username, email });
    await user.save();
    console.log('User saved successfully');
    res.status(201).json({ message: 'User registered successfully' });
  } catch (error) {
    console.error('Signup error:', error);
    res.status(500).json({ message: 'Error registering user' });
  }
});

app.post('/signin', async (req, res) => {
  try {
    const { email, password } = req.body;

    // Find user
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(400).json({ message: 'User not found' });
    }

    // Check password
    const validPassword = await bcrypt.compare(password, user.password);
    if (!validPassword) {
      return res.status(400).json({ message: 'Invalid password' });
    }

    // Generate JWT token
    const token = jwt.sign(
      { userId: user._id, email: user.email },
      'your_jwt_secret', // Replace with a secure secret key
      { expiresIn: '1h' }
    );

    res.json({
      message: 'Login successful',
      token,
      user: {
        id: user._id,
        username: user.username,
        email: user.email
      }
    });
  } catch (error) {
    console.error('Signin error:', error);
    res.status(500).json({ message: 'Error signing in' });
  }
});

// Middleware to verify JWT token
const verifyToken = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ message: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, 'your_jwt_secret');
    req.userId = decoded.userId;
    next();
  } catch (error) {
    return res.status(401).json({ message: 'Invalid token' });
  }
};

// Route to save processed image
app.post('/save-processed-image', verifyToken, async (req, res) => {
  try {
    console.log('Received save image request');
    const { imageData } = req.body;

    if (!imageData) {
      console.error('No image data provided');
      return res.status(400).json({ message: 'No image data provided' });
    }

    // Verify user exists
    const user = await User.findById(req.userId);
    if (!user) {
      console.error('User not found:', req.userId);
      return res.status(404).json({ message: 'User not found. Please sign in again.' });
    }

    // Extract the base64 data from the imageData string
    const base64Data = imageData.split(',')[1];
    if (!base64Data) {
      console.error('Invalid image data format');
      return res.status(400).json({ message: 'Invalid image data format' });
    }

    console.log('Base64 data length:', base64Data.length);
    console.log('First 50 characters of base64:', base64Data.substring(0, 50));

    // Update user's avatar with the actual processed image
    user.avatar = {
      contentType: 'image/jpeg',
      data: {
        $binary: {
          base64: base64Data,
          subType: '00'
        }
      }
    };

    // Save the user document
    await user.save();

    // Verify the save was successful
    const verifyUser = await User.findById(req.userId);
    console.log('Verification results:');
    console.log('User avatar exists:', !!verifyUser.avatar);
    console.log('User avatar data exists:', !!verifyUser.avatar?.data?.$binary?.base64);
    console.log('User avatar data length:', verifyUser.avatar?.data?.$binary?.base64?.length);

    console.log('Image saved successfully to user document');
    res.status(201).json({ 
      message: 'Image saved successfully', 
      userId: user._id,
      verification: {
        userAvatarSaved: !!verifyUser.avatar?.data?.$binary?.base64,
        avatarDataLength: verifyUser.avatar?.data?.$binary?.base64?.length
      }
    });
  } catch (error) {
    console.error('Error saving image:', error);
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({ message: 'Invalid token. Please sign in again.' });
    }
    res.status(500).json({ message: 'Error saving image: ' + error.message });
  }
});

// Route to get processed images
app.get('/processed-images', verifyToken, async (req, res) => {
  try {
    const images = await ProcessedImage.find({ userId: req.userId })
      .sort({ date: -1 });
    res.json(images);
  } catch (error) {
    res.status(500).json({ message: 'Error fetching images' });
  }
});

// Route to delete processed image
app.delete('/processed-images/:id', verifyToken, async (req, res) => {
  try {
    const image = await ProcessedImage.findOneAndDelete({
      _id: req.params.id,
      userId: req.userId
    });
    
    if (!image) {
      return res.status(404).json({ message: 'Image not found' });
    }
    
    res.json({ message: 'Image deleted successfully' });
  } catch (error) {
    res.status(500).json({ message: 'Error deleting image' });
  }
});

// Add a route to list all images for debugging
app.get('/list-images', verifyToken, async (req, res) => {
  try {
    const images = await User.findById(req.userId)
      .select('processedImages')
      .sort({ 'processedImages.date': -1 });
    
    console.log(`Found ${images.processedImages.length} images for user ${req.userId}`);
    res.json({
      count: images.processedImages.length,
      images: images.processedImages
    });
  } catch (error) {
    console.error('Error listing images:', error);
    res.status(500).json({ message: 'Error listing images: ' + error.message });
  }
});

// Get user's avatar
app.get('/user/avatar', verifyToken, async (req, res) => {
  try {
    const user = await User.findById(req.userId).select('avatar');
    if (!user || !user.avatar || !user.avatar.data || !user.avatar.data.$binary || !user.avatar.data.$binary.base64) {
      return res.status(404).json({ message: 'Avatar not found' });
    }

    // Return the avatar data in the correct format
    res.json({
      contentType: user.avatar.contentType,
      data: user.avatar.data.$binary.base64
    });
  } catch (error) {
    console.error('Error fetching avatar:', error);
    res.status(500).json({ message: 'Error fetching avatar' });
  }
});

// Add a route to verify image storage
app.get('/verify-image-storage', verifyToken, async (req, res) => {
  try {
    const user = await User.findById(req.userId);
    const processedImages = await ProcessedImage.find({ userId: req.userId });

    res.json({
      userAvatar: {
        exists: !!user.avatar,
        hasData: !!user.avatar?.data,
        contentType: user.avatar?.contentType,
        dataLength: user.avatar?.data?.length
      },
      processedImages: {
        count: processedImages.length,
        latest: processedImages.length > 0 ? {
          id: processedImages[0]._id,
          date: processedImages[0].date,
          hasData: !!processedImages[0].imageData,
          dataLength: processedImages[0].imageData?.length
        } : null
      }
    });
  } catch (error) {
    console.error('Error verifying image storage:', error);
    res.status(500).json({ message: 'Error verifying image storage' });
  }
});

// Route to get user profile
app.get('/user/profile', verifyToken, async (req, res) => {
  try {
    const user = await User.findById(req.userId).select('-password');
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    res.json({
      username: user.username,
      email: user.email,
      avatar: user.avatar
    });
  } catch (error) {
    console.error('Error fetching user profile:', error);
    res.status(500).json({ message: 'Error fetching user profile' });
  }
});

// Route to get user profile data
app.get('/user-profile', verifyToken, async (req, res) => {
  try {
    const user = await User.findById(req.userId).select('-password');
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }
    res.json(user);
  } catch (error) {
    console.error('Error fetching user profile:', error);
    res.status(500).json({ message: 'Error fetching user profile' });
  }
});

// Start the server
const PORT = process.env.PORT || 5001;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
