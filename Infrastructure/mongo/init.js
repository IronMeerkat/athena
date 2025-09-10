// Initialize MongoDB 'sensitive' database with predefined collections and validators
// Collections: User, Location, Schedule

// Ensure we are operating on the 'sensitive' database
const dbName = 'sensitive';
const db = db.getSiblingDB(dbName);

// Helper to create a collection with schema validator if it doesn't exist
function ensureCollection(name, options) {
  const exists = db.getCollectionNames().includes(name);
  if (!exists) {
    db.createCollection(name, options || {});
  } else if (options && options.validator) {
    // Apply validator only if not present; safely set via collMod
    const collInfo = db.getCollectionInfos({ name })[0] || {};
    const hasValidator = collInfo.options && collInfo.options.validator;
    if (!hasValidator) {
      db.runCommand({
        collMod: name,
        validator: options.validator,
        validationLevel: options.validationLevel || 'moderate',
        validationAction: options.validationAction || 'error',
      });
    }
  }
}

// User collection schema and indexes
ensureCollection('User', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['username'],
      additionalProperties: true,
      properties: {
        _id: { bsonType: 'objectId' },
        username: { bsonType: 'string', description: 'unique username' },
        email: { bsonType: ['string', 'null'] },
        created_at: { bsonType: ['date', 'null'] },
      },
    },
  },
  validationLevel: 'moderate',
  validationAction: 'error',
});
db.User.createIndex({ username: 1 }, { unique: true, name: 'uniq_username' });

// Location collection schema and indexes
ensureCollection('Location', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name'],
      additionalProperties: true,
      properties: {
        _id: { bsonType: 'objectId' },
        user_key: { bsonType: ['string', 'null'] },
        name: { bsonType: 'string' },
        address: { bsonType: ['string', 'null'] },
        coordinates: {
          bsonType: ['object', 'null'],
          properties: {
            lat: { bsonType: 'double' },
            lng: { bsonType: 'double' },
          },
        },
        radius: {
          bsonType: ['double', 'null'],
          description: 'geofence radius in meters'
        },
        created_at: { bsonType: ['date', 'null'] },
      },
    },
  },
  validationLevel: 'moderate',
  validationAction: 'error',
});
db.Location.createIndex({ name: 1 }, { name: 'idx_name' });
db.Location.createIndex({ user_key: 1 }, { name: 'idx_user_key' });
db.Location.createIndex({ coordinates: '2dsphere' }, { name: 'idx_geospatial' });

// Schedule collection schema and indexes
ensureCollection('Schedule', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_key', 'blocks'],
      additionalProperties: true,
      properties: {
        _id: { bsonType: 'objectId' },
        user_key: { bsonType: 'string' },
        blocks: {
          bsonType: 'array',
          items: {
            bsonType: 'object',
            required: ['start_minutes', 'end_minutes', 'strictness'],
            properties: {
              start_minutes: { bsonType: 'int' },
              end_minutes: { bsonType: 'int' },
              strictness: { bsonType: 'int' },
              goal: { bsonType: ['string', 'null'] },
              days: {
                bsonType: ['array', 'null'],
                items: { bsonType: 'int' },
              },
            },
          },
        },
        created_at: { bsonType: ['date', 'null'] },
      },
    },
  },
  validationLevel: 'moderate',
  validationAction: 'error',
});
db.Schedule.createIndex({ user_key: 1 }, { name: 'idx_user_key' });


