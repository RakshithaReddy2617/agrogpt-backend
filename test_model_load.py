import tensorflow as tf

MODEL_PATH = r"C:\Users\J RAKSHITHA\Documents\projects\agrogpt-backend\binary_classification\agro_classifier_FINAL_CLEAN.keras"

try:
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    print("✅ Model loaded successfully")
    model.summary()
except Exception as e:
    print("❌ Model failed to load")
    print(e)
