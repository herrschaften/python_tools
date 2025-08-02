// 3D Sphere Cloud with Raymarching + Pixelation
// Copy and paste this into Shadertoy

// === VISUAL PARAMETERS ===
#define PIXEL_SIZE 64.0              // Lower = more detail, higher = more pixelated
#define SKY_COLOR vec3(0.4, 0.7, 1.0) // Background color

// === CLOUD STRUCTURE ===
#define CLOUD_CENTER vec3(0.0, 0.0, -5.0)  // Position of cloud center
#define NUM_SPHERES 25               // Number of spheres making up the cloud
#define SPHERE_SIZE_MIN 0.3          // Minimum sphere radius
#define SPHERE_SIZE_RANGE 0.8        // Additional random size range
#define CLOUD_WIDTH .8              // How wide the cloud spreads horizontally
#define CLOUD_HEIGHT 0.4             // How tall the cloud is vertically

// === MOVEMENT & ANIMATION ===
#define ANIMATION_SPEED .13         // Overall speed of all animation
#define ORBITAL_SPEED 1.0            // Speed of sphere rotation around center
#define VERTICAL_BOB_AMOUNT .85      // How much spheres bob up and down
#define ORBIT_RADIUS_MIN 0.01         // Minimum distance from center
#define ORBIT_RADIUS_RANGE 2.5       // Additional random orbit distance

// === LIGHTING ===
#define LIGHT_DIRECTION vec3(-0.5, 1.0, 0.3)  // Sun direction
#define AMBIENT_LIGHT 0.3            // Base lighting level
#define DIFFUSE_STRENGTH 0.7         // Directional light strength
#define SPECULAR_STRENGTH 0.5        // Highlight strength
#define SPECULAR_SHARPNESS 16.0      // How sharp highlights are

// === COLOR PALETTE ===
#define COLOR_LEVELS 6.0             // Number of discrete lighting levels
#define BRIGHT_HIGHLIGHT vec3(1.0, 1.0, 1.0)
#define LIGHT_HIGHLIGHT vec3(0.95, 0.97, 1.0)
#define MEDIUM_LIGHT vec3(0.85, 0.9, 0.95)
#define LIGHT_SHADOW vec3(0.7, 0.75, 0.85)
#define MEDIUM_SHADOW vec3(0.55, 0.6, 0.75)
#define DEEP_SHADOW vec3(0.4, 0.45, 0.65)

// ==========================================

// Hash functions for procedural generation
float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.3, 311.7))) * 43758.5453123);
}

// Signed Distance Function for a sphere
float sphereSDF(vec3 p, vec3 center, float radius) {
    return length(p - center) - radius;
}

// Generate cloud using multiple spheres in orbital arrangement
float cloudSDF(vec3 p) {
    float time = iTime * ANIMATION_SPEED;
    vec3 center = CLOUD_CENTER;
    
    float cloud = 999.0; // Start with large distance (no hit)
    
    // Create each sphere in the cloud
    for(int i = 0; i < NUM_SPHERES; i++) {
        float fi = float(i);
        
        // Orbital position calculation
        float angle = fi * 2.4 + time * ORBITAL_SPEED;  // Each sphere has unique angle + rotation
        float height = hash(fi * 0.1) * 2.0 - 1.0;      // Random height layer (-1 to +1)
        float orbit_radius = hash(fi * 0.2) * ORBIT_RADIUS_RANGE + ORBIT_RADIUS_MIN;
        
        // Calculate sphere position
        vec3 spherePos = center + vec3(
            cos(angle) * orbit_radius * CLOUD_WIDTH,    // X: orbital motion
            height * CLOUD_HEIGHT + sin(time + fi) * VERTICAL_BOB_AMOUNT, // Y: height + bobbing
            sin(angle) * orbit_radius * CLOUD_WIDTH     // Z: orbital motion
        );
        
        // Calculate sphere size
        float sphereSize = SPHERE_SIZE_MIN + hash(fi * 0.3) * SPHERE_SIZE_RANGE;
        
        // Add this sphere to the cloud (union operation - take closest)
        float sphere = sphereSDF(p, spherePos, sphereSize);
        cloud = min(cloud, sphere);
    }
    
    return cloud;
}

// March a ray through the scene to find intersections
float raymarch(vec3 ro, vec3 rd) {
    float t = 0.0;              // Current distance along ray
    float maxDist = 20.0;       // Maximum render distance
    
    for(int i = 0; i < 64; i++) {
        vec3 p = ro + rd * t;   // Current position along ray
        float d = cloudSDF(p);  // Distance to closest surface
        
        if(d < 0.01) {
            return t; // Hit surface - return distance
        }
        
        if(t > maxDist) {
            return -1.0; // Ray went too far - missed everything
        }
        
        t += d * 0.5; // Step forward (reduced step size for accuracy)
    }
    
    return -1.0; // Ran out of steps - missed
}

// Calculate surface normal using finite differences
vec3 getNormal(vec3 p) {
    float eps = 0.01; // Small offset for numerical differentiation
    return normalize(vec3(
        cloudSDF(p + vec3(eps, 0, 0)) - cloudSDF(p - vec3(eps, 0, 0)),
        cloudSDF(p + vec3(0, eps, 0)) - cloudSDF(p - vec3(0, eps, 0)),
        cloudSDF(p + vec3(0, 0, eps)) - cloudSDF(p - vec3(0, 0, eps))
    ));
}

// Calculate lighting using Phong shading model
float calculateLighting(vec3 p, vec3 normal) {
    vec3 lightDir = normalize(LIGHT_DIRECTION);  // Direction to light source
    vec3 viewDir = normalize(-p);                // Direction to camera (at origin)
    
    // Diffuse lighting (Lambert)
    float diffuse = max(0.0, dot(normal, lightDir));
    
    // Ambient lighting (constant base light)
    float ambient = AMBIENT_LIGHT;
    
    // Specular lighting (Phong reflection)
    vec3 reflectDir = reflect(-lightDir, normal);
    float specular = pow(max(0.0, dot(viewDir, reflectDir)), SPECULAR_SHARPNESS) * SPECULAR_STRENGTH;
    
    return ambient + diffuse * DIFFUSE_STRENGTH + specular;
}

// Convert continuous lighting to discrete pixel-art color palette
vec3 lightingToColor(float lighting) {
    // Quantize lighting to create distinct color bands
    lighting = floor(lighting * COLOR_LEVELS) / COLOR_LEVELS;
    
    // Map lighting levels to specific colors (brightest to darkest)
    if(lighting > 0.9) return BRIGHT_HIGHLIGHT;
    if(lighting > 0.75) return LIGHT_HIGHLIGHT;
    if(lighting > 0.6) return MEDIUM_LIGHT;
    if(lighting > 0.45) return LIGHT_SHADOW;
    if(lighting > 0.3) return MEDIUM_SHADOW;
    return DEEP_SHADOW;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Convert pixel coordinates to UV coordinates (0-1 range)
    vec2 uv = fragCoord / iResolution.xy;
    
    // Apply pixelation effect by quantizing UV coordinates
    vec2 pixelUV = floor(uv * PIXEL_SIZE) / PIXEL_SIZE;
    
    // Convert to Normalized Device Coordinates (-1 to +1 range)
    vec2 ndc = pixelUV * 2.0 - 1.0;
    ndc.x *= iResolution.x / iResolution.y; // Correct for aspect ratio
    
    // Set up camera and ray
    vec3 rayOrigin = vec3(0.0, 0.0, 0.0);          // Camera at origin
    vec3 rayDirection = normalize(vec3(ndc, -1.0)); // Ray direction (perspective projection)
    
    // March the ray through the scene
    float t = raymarch(rayOrigin, rayDirection);
    
    vec3 finalColor = SKY_COLOR; // Default to sky color
    
    if(t > 0.0) {
        // Ray hit the cloud - calculate lighting and shading
        vec3 hitPoint = rayOrigin + rayDirection * t;
        vec3 normal = getNormal(hitPoint);
        float lighting = calculateLighting(hitPoint, normal);
        
        finalColor = lightingToColor(lighting);
    }
    
    fragColor = vec4(finalColor, 1.0);
}