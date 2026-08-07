/**
 * 通过插桩记录方法调用、参数、返回值和副作用，为 isolated validation 生成原始日志。
 */
package com.example.minimal;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.security.CodeSource;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.Set;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.aspectj.lang.Signature; 
import org.aspectj.lang.reflect.ConstructorSignature;
import org.aspectj.lang.reflect.MethodSignature;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import org.reflections.Reflections;
import org.reflections.scanners.SubTypesScanner;
import org.reflections.util.ClasspathHelper;
import org.reflections.util.ConfigurationBuilder;


@Aspect
public class LoggingAspect {

    public static String previousTestMethod;
    public static String currentTestClass;
    public static String currentTestMethod;
    public static Set processedMethods = new HashSet<String>();
    
    @Pointcut("execution(* com.example.minimal..*(..)) && " +
            "!execution(* com.example.minimal..*Test.*(..)) && " +
            "!execution(* com.example.minimal..*TestCase.*(..)) && " +
            "!@annotation(org.junit.Test)")
    public void applicationMethods() {}

    @Pointcut("execution(* com.example.minimal.LoggingAspect.*(..))")
    public void loggingAspectMethods() {}

    @Pointcut("execution(* com.example.minimal.CustomToStringConverter.*(..))")
    public void customToStringConverterMethods() {}

    @Pointcut("execution(com.example.minimal..new(..)) && " +
            "!execution(com.example.minimal.LoggingAspect.new(..)) && " +
            "!execution(com.example.minimal.CustomToStringConverter.new(..)) &&" +
            "!execution(com.example.minimal..*Test.new(..)) && " +
            "!execution(com.example.minimal..*TestCase.new(..))")
    public void applicationConstructors() {}

    @Around("applicationConstructors()")
    public Object logConstructor(ProceedingJoinPoint joinPoint) throws Throwable {
        Class<?> clazz = joinPoint.getSignature().getDeclaringType();
        
        // Skip constructors of abstract classes
        if (Modifier.isAbstract(clazz.getModifiers())) {
            return joinPoint.proceed();
        }

        return logMethodVariables(joinPoint);
    }


    @Around("applicationMethods() && !applicationConstructors() && !loggingAspectMethods() && !customToStringConverterMethods()")
    public Object logMethodVariables(ProceedingJoinPoint joinPoint) throws Throwable {
        Signature signature = joinPoint.getSignature();
        if (signature instanceof MethodSignature) {
            Method method = ((MethodSignature) signature).getMethod();
            if (method.getName().equals("newUndirectedMutableGraph") || 
                method.getName().equals("newDirectedMutableGraph") ||
                (method.getName().equals("checkNotNull") && joinPoint.getSignature().getDeclaringTypeName().contains("Assertions")) ||
                (method.getName().equals("withConnections") && joinPoint.getSignature().getDeclaringTypeName().contains("DefaultLinkedConnectionBuilder")) ||
                (method.getName().equals("connect1") && joinPoint.getSignature().getDeclaringTypeName().contains("AbstractGraphConnection")) ||
                (method.getName().equals("connect") && joinPoint.getSignature().getDeclaringTypeName().contains("AbstractGraphConnection")) ||
                (method.getName().equals("addVertex") && joinPoint.getSignature().getDeclaringTypeName().contains("AbstractGraphConnection")) ||
                (method.getName().equals("addEdge") && joinPoint.getSignature().getDeclaringTypeName().contains("AbstractGraphConnection"))) {
                return joinPoint.proceed(); // edge case (multiple anonymous classes - cannot distinguish)
            }
            if (method.isSynthetic()) {
                return joinPoint.proceed(); // Skip synthetic methods
            }
            if (method.getDeclaringClass().isEnum()) {
                String methodName = method.getName();
                if (methodName.equals("valueOf") || methodName.equals("values")) {
                    return joinPoint.proceed(); // Skip enum built-in methods
                }
            }
            Class<?> declaringClass = method.getDeclaringClass();
            CodeSource codeSource = declaringClass.getProtectionDomain().getCodeSource();
            if (codeSource != null) {
                String path = codeSource.getLocation().getPath();
                if (path.contains("test-classes")) {
                    return joinPoint.proceed(); // Skip methods defined in test scope
                }
            }
        }
        else if (signature instanceof ConstructorSignature) {
            Constructor<?> constructor = ((ConstructorSignature) signature).getConstructor();
            if (constructor.isSynthetic()) {
                return joinPoint.proceed(); // Skip synthetic constructors
            }
            Class<?> declaringClass = constructor.getDeclaringClass();
            if (declaringClass.isEnum()) {
                return joinPoint.proceed(); // Skip constructors of enums
            }
            CodeSource codeSource = declaringClass.getProtectionDomain().getCodeSource();
            if (codeSource != null) {
                String path = codeSource.getLocation().getPath();
                if (path.contains("test-classes")) {
                    return joinPoint.proceed(); // Skip constructors *defined* in test classes
                }
            }
        
            // Also check what class the *constructed instance* is
            Object target = joinPoint.getThis();
            if (target != null) {
                CodeSource instanceCodeSource = target.getClass().getProtectionDomain().getCodeSource();
                if (instanceCodeSource != null) {
                    String instancePath = instanceCodeSource.getLocation().getPath();
                    if (instancePath.contains("test-classes")) {
                        return joinPoint.proceed(); // Skip if *constructed object* is from test classes
                    }
                }
            }
        }
        Object[] args = joinPoint.getArgs();
        if (joinPoint.getSignature() instanceof ConstructorSignature) {
            ConstructorSignature sig = (ConstructorSignature) joinPoint.getSignature();
            Class<?> declaringClass = sig.getDeclaringType();
            Class<?> enclosing = declaringClass.getEnclosingClass();
            if (enclosing != null && args.length > 0 && enclosing.isInstance(args[0])) {
                args = Arrays.copyOfRange(args, 1, args.length);
            }
        }
        String methodName = joinPoint.getSignature().getName();
        String className = joinPoint.getSignature().getDeclaringTypeName();
        if (processingJUnitSetUpMethod()) {
            currentTestClass = findLastTestClassInStackTrace(Thread.currentThread().getStackTrace());
            currentTestMethod = null;
        } else if (currentTestClass != null && currentTestMethod == null) {
            currentTestMethod = findLastTestMethodInStackTrace(Thread.currentThread().getStackTrace());
        } else if (currentTestClass != null && currentTestMethod != null) {
            if (!currentTestMethod.equals(findLastTestMethodInStackTrace(Thread.currentThread().getStackTrace()))) {
                currentTestClass = null;
                currentTestMethod = null;
            }
        }
        String testMethodBeingProcessed = findLastTestMethodInStackTrace(Thread.currentThread().getStackTrace());
        if (!testMethodBeingProcessed.equals(previousTestMethod)) {
            markPreviousMethodProcessed();
            previousTestMethod = testMethodBeingProcessed;
        }
        if (processingJUnitLifecycleMethod()) {
            if (methodProcessed()) {
                return joinPoint.proceed(); // skip repetitively logging JUnit lifecycle methods
            }
        }
        appendToLogFile("==========START OF " + className + "." + methodName + "==========");
        int modifiers = -1;
        if (signature instanceof MethodSignature) {
            MethodSignature methodSignature = (MethodSignature)signature;
            Method method = methodSignature.getMethod();
            modifiers = method.getModifiers();
        } else {
            ConstructorSignature constructorSignature = (ConstructorSignature)signature;
            Constructor constructor = constructorSignature.getConstructor();
            modifiers = constructor.getModifiers();
        }
        String modifer = "public";
        if (Modifier.isPrivate(modifiers)) {
            modifer = "private";
        } else if (Modifier.isProtected(modifiers)) {
            modifer = "protected";
        }


        Object instance = joinPoint.getTarget();
        boolean calledOnInstance = false;

        // Track mutable params
        List<Integer> originalParams = new ArrayList<>();
        List<String> allLogs = new ArrayList<>();
        if (instance != null) {
            calledOnInstance = true;
        }

        if (calledOnInstance) {
            allLogs.add("Instance Initial: " + CustomToStringConverter.customToJSONObject(instance).toString());
        }

        for (int i = 0; i < args.length; i++) {
            originalParams.add(i);
            Object currentValue = args[i];
            allLogs.add(("Arg" + i + " initial state: " + CustomToStringConverter.customToJSONObject(currentValue).toString()));
        }

        // Capture static fields
        Map<Class<?>, Map<String, Object>> originalStaticValues = new HashMap<>();
        Set<Class<?>> allClasses = getAllClasses();
        for (Class<?> clazz : allClasses) {
            String path = clazz.getProtectionDomain().getCodeSource().getLocation().getPath();
            if (path.contains("/test-classes/")) {
                continue; // Skip test classes
            } 
            if (clazz.getName().contains("com.example.minimal") || clazz.getName().startsWith("java.")) {
                if (!clazz.isInterface() && !clazz.getSimpleName().equals("CustomToStringConverter")) {
                    captureStaticFields(clazz, originalStaticValues);
                }
            }
        }
        JSONArray allStaticFields = new JSONArray();
        for (Class<?> clazz : allClasses) {
            try {
                if (clazz.getSimpleName().equals("CustomToStringConverter")) {
                    continue;
                }
            } catch (Throwable t) {
                continue;
            }
            JSONObject classStaticFields = getStaticFieldsInfo(clazz, originalStaticValues, false);
            if (!classStaticFields.isEmpty()) {
                allStaticFields.put(classStaticFields);
            }
        }
        if (!allStaticFields.isEmpty()) {
            allLogs.add("Static Fields Initial: " + allStaticFields);
        }

        Object result = null;
        try {
            if (joinPoint.getSignature().getName().equals("<init>")) {
                result = joinPoint.getTarget();  // `joinPoint.getTarget()` is the newly created object
                joinPoint.proceed();
            } else {
                try {
                    result = joinPoint.proceed();
                } catch (NullPointerException npe) {
                    npe.printStackTrace();
                    throw npe;
                }   
            }
        } catch (Exception e) {
            allLogs.add("Exception thrown: " + CustomToStringConverter.customToJSONObject(e).toString());
            appendToLogFile(className + "." + methodName + "[" + modifer + ":" + allLogs);
            appendToLogFile("==========END OF " + className + "." + methodName + "==========");
            throw e;
        }

        // Capture changes to static fields
        JSONArray allClassChanges = new JSONArray();
        for (Class<?> clazz : allClasses) {
            try {
                if (clazz.getSimpleName().equals("CustomToStringConverter")) {
                    continue;
                }
            } catch (Throwable t) {
                continue;
            }
            JSONObject classChange = getStaticFieldsInfo(clazz, originalStaticValues, true);
            if (!classChange.isEmpty()) {
                allClassChanges.put(classChange);
            }
        }
        if (!allClassChanges.isEmpty()) {
            allLogs.add("Static Fields Changed: " + allClassChanges);
        }

        if (calledOnInstance) {
            allLogs.add("Instance Final: " + CustomToStringConverter.customToJSONObject(instance).toString());
        }

        for (int j = 0; j < args.length; j++) {
            if (originalParams.contains(j)) {
                Object currentValue = args[j];
                allLogs.add(("Arg" + j + " final state: " + CustomToStringConverter.customToJSONObject(currentValue).toString()));
            }
        }


        if (result != null) {
            allLogs.add(("Return value: " + CustomToStringConverter.customToJSONObject(result).toString()));
        }

        appendToLogFile(className + "." + methodName + "[" + modifer + ":" + allLogs);
        appendToLogFile("==========END OF " + className + "." + methodName + "==========");
        return result;  // For non-constructor methods, return the result of the method execution
    }

    public static boolean processingJUnitLifecycleMethod() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
        for (int i = stackTrace.length - 1; i >= 0; i--) {
            StackTraceElement element = stackTrace[i];
            try {
                Class<?> clazz = Class.forName(element.getClassName());
                Method method = getMethod(clazz, element.getMethodName());

                if (method != null) {
                    if (method.isAnnotationPresent(Before.class) ||
                        method.isAnnotationPresent(BeforeEach.class) ||
                        method.isAnnotationPresent(After.class) ||
                        method.isAnnotationPresent(AfterEach.class)) {
                            return true;
                        }
                }
            } catch (ClassNotFoundException e) {
                continue;
            }
        }
        return false;
    }

    public static boolean processingJUnitSetUpMethod() {
        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
        for (int i = stackTrace.length - 1; i >= 0; i--) {
            StackTraceElement element = stackTrace[i];
            try {
                Class<?> clazz = Class.forName(element.getClassName());
                Method method = getMethod(clazz, element.getMethodName());

                if (method != null) {
                    if (method.isAnnotationPresent(Before.class) ||
                        method.isAnnotationPresent(BeforeEach.class)) {
                            return true;
                        }
                }
            } catch (ClassNotFoundException e) {
                continue;
            }
        }
        return false;
    }

    private static Method getMethod(Class<?> clazz, String methodName) {
        while (clazz != null) {
            for (Method method : clazz.getDeclaredMethods()) {
                if (method.getName().equals(methodName)) {
                    return method;
                }
            }
            clazz = clazz.getSuperclass(); // Traverse up in case of inheritance
        }
        return null;
    }

    private static void appendToLogFile(String logMessage) {
        try {
            String testName = findLastTestMethodInStackTrace(Thread.currentThread().getStackTrace());
            if (testName == null) return;
    
            File logFile = new File(testName + ".log");
            try (BufferedWriter writer = new BufferedWriter(new FileWriter(logFile, true))) {
                writer.write(logMessage);
                writer.newLine();
            }
        } catch (IOException e) {
            System.err.println("Logging failed: " + e.getMessage());
        }
    }

    public static String findLastTestClassInStackTrace(StackTraceElement[] stackTrace) {
        Pattern testClassPattern = Pattern.compile(".*(Test|TestCase)$");

        for (int i = stackTrace.length - 1; i >= 0; i--) {
            StackTraceElement element = stackTrace[i];
            try {
                if (testClassPattern.matcher(element.getClassName()).matches()) {
                    Class<?> elementClass = Class.forName(element.getClassName());
                    return elementClass.getName();
                }
            } catch (ClassNotFoundException e) {
                continue;
            }
        }
        return null;
    }
    
    public static String findLastTestMethodInStackTrace(StackTraceElement[] stackTrace) {
        Pattern testClassPattern = Pattern.compile(".*(Test|TestCase)$");

        for (int i = stackTrace.length - 1; i >= 0; i--) {
            StackTraceElement element = stackTrace[i];
            try {
                String className = element.getClassName();
                if (testClassPattern.matcher(className).matches()
                    && !className.equals("junit.framework.TestCase")) {
                    Class<?> elementClass = Class.forName(className);
                    if (currentTestClass != null) {
                        return currentTestClass + "." + element.getMethodName();
                    } else {
                        return elementClass.getName() + "." + element.getMethodName();
                    }
                }
            } catch (ClassNotFoundException e) {
                continue;
            }
        }
        return null;
    }

    public static void markPreviousMethodProcessed() {
        try {
            if (previousTestMethod == null) return;
            processedMethods.add(previousTestMethod);
        } catch (Exception e) {
            System.err.println("Error when marking the previous method as processed: " + e.getMessage());
            return;
        }
    }

    public static boolean methodProcessed() {
        try {
            String testName = findLastTestMethodInStackTrace(Thread.currentThread().getStackTrace());
            if (testName == null) return false;
            return processedMethods.contains(testName);
        } catch (Exception e) {
            System.err.println("Error when checking if the current method is processed: " + e.getMessage());
            return false;
        }
    }
    
    public static Set<Class<?>> getAllClasses() {
        String fullPackage = null;
        Package objPackage = LoggingAspect.class.getPackage();
        if (objPackage != null) {
            fullPackage = objPackage.getName();
        }
        Set<String> packageOfLargeStaticFields = Collections.unmodifiableSet(
            new HashSet<>(Arrays.asList(
                "org.apache.commons.codec",
                "me.lemire",
                "com.kamikaze",
                "org.apache.commons.validator",
                "org.fusesource.jansi"
            ))
        );
        for (String pkg : packageOfLargeStaticFields) {
            if (fullPackage.contains(pkg)) {
                return new HashSet<>();
            }
        }
    
        String[] basePackageParts = fullPackage != null ? fullPackage.split("\\.") : new String[0];
        String basePackage = "";
        if (basePackageParts.length > 2) {
            basePackage = basePackageParts[0] + "." + basePackageParts[1];
        }
    
        Reflections reflections = new Reflections(new ConfigurationBuilder()
            .setUrls(ClasspathHelper.forPackage(basePackage))
            .setScanners(new SubTypesScanner(false)));
    
        Set<Class<?>> safeClasses = new HashSet<>();
        for (Class<?> clazz : reflections.getSubTypesOf(Object.class)) {
            try {
                if (clazz == null || clazz.isEnum() || clazz.equals(LoggingAspect.class)) {
                    continue;
                }
                safeClasses.add(clazz);
            } catch (Throwable t) {
                // Skip classes that fail to load properly
            }
        }
    
        return safeClasses;
    }
    

    public static void captureStaticFields(
        Class<?> clazz, 
        Map<Class<?>, Map<String, Object>> originalStaticValues
    ) throws IllegalAccessException {
        Map<String, Object> staticValues = new HashMap<>();
        for (Field field : clazz.getDeclaredFields()) {
            if (java.lang.reflect.Modifier.isStatic(field.getModifiers())) {
                field.setAccessible(true);
                try {
                    Object value = field.get(null);
                    staticValues.put(field.getName(), value);
                } catch (Throwable t) {
                    continue;
                }
            }
        }
        originalStaticValues.put(clazz, staticValues);
    }

    public static JSONObject getStaticFieldsInfo(Class<?> clazz, Map<Class<?>, Map<String, Object>> originalStaticValues, boolean afterExecution) throws IllegalAccessException {
        Map<String, Object> originalValues = originalStaticValues.get(clazz);
        JSONObject classChange = new JSONObject();
        JSONObject classInitial = new JSONObject();
        if (originalValues != null) {
            JSONArray fieldChanges = new JSONArray();
            JSONArray originalFields = new JSONArray();

            for (Field field : clazz.getDeclaredFields()) {
                if (field.getName().contains("$jacocoData") || field.getName().contains("ajc$")) {
                    continue;
                }
                if (java.lang.reflect.Modifier.isStatic(field.getModifiers())) {
                    if (!originalValues.containsKey(field.getName())) {
                        continue;
                    }
                    field.setAccessible(true);
                    Object newValue = field.get(null);
                    Object originalValue = originalValues.get(field.getName());
                    int modifiers = field.getModifiers();
                    
                    if (!afterExecution) {
                        JSONObject originalField = new JSONObject();
                        JSONObject originalFieldDetails = new JSONObject();
                        if (Modifier.isPrivate(modifiers)) {
                            originalFieldDetails.put("modifier", "private");
                        } else if (Modifier.isProtected(modifiers)) {
                            originalFieldDetails.put("modifier", "protected");
                        } else {
                            originalFieldDetails.put("modifier", "public");
                        }
                        originalFieldDetails.put("details", CustomToStringConverter.customToJSONObject(originalValue));
                        originalField.put(field.getName(), originalFieldDetails);
                        originalFields.put(originalField);
                    } else {
                        if (overridesEquals(newValue)) {
                            JSONObject changedField = new JSONObject();
                            JSONObject changedFieldDetails = new JSONObject();
                            if (Modifier.isPrivate(modifiers)) {
                                changedFieldDetails.put("modifier", "private");
                            } else if (Modifier.isProtected(modifiers)) {
                                changedFieldDetails.put("modifier", "protected");
                            } else {
                                changedFieldDetails.put("modifier", "public");
                            }
                            changedFieldDetails.put("details", CustomToStringConverter.customToJSONObject(field.get(null)));
                            changedField.put(field.getName(), changedFieldDetails);
                            fieldChanges.put(changedField);
                        } else if ((newValue != null && !newValue.equals(originalValue)) || (newValue == null && originalValue != null)) {
                            JSONObject changedField = new JSONObject();
                            JSONObject changedFieldDetails = new JSONObject();
                            if (Modifier.isPrivate(modifiers)) {
                                changedFieldDetails.put("modifier", "private");
                            } else if (Modifier.isProtected(modifiers)) {
                                changedFieldDetails.put("modifier", "protected");
                            } else {
                                changedFieldDetails.put("modifier", "public");
                            }
                            changedFieldDetails.put("details", CustomToStringConverter.customToJSONObject(field.get(null)));
                            changedField.put(field.getName(), changedFieldDetails);
                            fieldChanges.put(changedField);
                        }
                    }
                }
            }
            if (afterExecution && !fieldChanges.isEmpty()) {
                if (CustomToStringConverter.isTestClass(clazz)) {
                    classChange.put("src.test." + clazz.getName(), fieldChanges);
                } else {
                    classChange.put("src.main." + clazz.getName(), fieldChanges);
                }
            }
            if (!afterExecution && !originalFields.isEmpty()) {
                if (CustomToStringConverter.isTestClass(clazz)) {
                    classInitial.put("src.test." + clazz.getName(), originalFields);
                } else {
                    classInitial.put("src.main." + clazz.getName(), originalFields);
                }
            }
        }
        if (afterExecution) {
            return classChange;
        }
        return classInitial;
    }

    public static boolean overridesEquals(Object obj) {
        if (obj == null) return false;
        Class<?> clazz = obj.getClass();
        try {
            Method equalsMethod = clazz.getMethod("equals", Object.class);
            return !equalsMethod.getDeclaringClass().equals(Object.class);
        } catch (NoSuchMethodException e) {
            return false; // Should never happen because Object defines equals()
        }
    }
}
