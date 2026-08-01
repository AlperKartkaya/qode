import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, SafeAreaView, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { showToast } from '../utils/toast';
import { verifyNumber } from '../utils/api';

export default function NumberVerifyScreen({ navigation }) {
  const [phoneNumber, setPhoneNumber] = useState('+905390000020');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [isLogExpanded, setIsLogExpanded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const addLog = (msg) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const handleVerify = async () => {
    setLoading(true);
    setHasError(false);
    setLogs([]);
    setIsLogExpanded(false);
    
    try {
      addLog('Initiating OIDC Authorization Code (3-legged) flow...');
      addLog('Sending POST /verify to OpenGateway...');
      showToast('Initiating cellular network verification...');
      
      const result = await verifyNumber(phoneNumber);
      addLog(`Received response: ${JSON.stringify(result)}`);
      
      if (result.devicePhoneNumberVerified) {
        addLog('devicePhoneNumberVerified: true');
        showToast('Number verified successfully!');
        // Çapraz geçiş (App.js'de animation: 'fade' ayarlandı)
        navigation.replace('Home', { phoneNumber });
      } else {
        setHasError(true);
        addLog('Verification Failed: Number mismatch or network issue.');
        showToast('Sign-in failed', true);
      }
    } catch (error) {
      setHasError(true);
      addLog(`Error: ${error.message || 'Unknown network error'}`);
      showToast('Sign-in failed', true);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Ionicons name="shield-checkmark" size={48} color="#4338CA" />
          </View>
          <Text style={styles.title}>Secure Login</Text>
          <Text style={styles.subtitle}>VERİFY YOUR NUMBER</Text>
        </View>
        
        <View style={styles.inputContainer}>
          <Ionicons name="call-outline" size={20} color="#6B7280" style={styles.inputIcon} />
          <TextInput
            style={styles.input}
            value={phoneNumber}
            onChangeText={setPhoneNumber}
            keyboardType="phone-pad"
            placeholder="Enter MSISDN"
            placeholderTextColor="#9CA3AF"
          />
        </View>
        
        <TouchableOpacity 
          style={[styles.button, loading && styles.buttonDisabled]} 
          onPress={handleVerify}
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Sign in</Text>
          )}
        </TouchableOpacity>

        {hasError && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>Sign-in failed</Text>
            
            <TouchableOpacity 
              style={styles.logHeader} 
              onPress={() => setIsLogExpanded(!isLogExpanded)}
            >
              <Text style={styles.logTitle}>Connection logs</Text>
              <Ionicons name={isLogExpanded ? "chevron-up" : "chevron-down"} size={20} color="#6B7280" />
            </TouchableOpacity>
            
            {isLogExpanded && (
              <View style={styles.logBox}>
                {logs.map((l, i) => (
                  <Text key={i} style={styles.logItem}>{l}</Text>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#F3F4F6' },
  container: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  header: { alignItems: 'center', marginBottom: 40 },
  iconContainer: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#EEF2FF', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  title: { fontSize: 28, fontWeight: '800', color: '#111827', marginBottom: 8 },
  subtitle: { fontSize: 13, color: '#4338CA', fontWeight: '700', letterSpacing: 1 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 12, paddingHorizontal: 16, height: 56, marginBottom: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 2 },
  inputIcon: { marginRight: 12 },
  input: { flex: 1, fontSize: 16, color: '#111827' },
  button: { backgroundColor: '#4338CA', height: 56, borderRadius: 12, justifyContent: 'center', alignItems: 'center', shadowColor: '#4338CA', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.2, shadowRadius: 8, elevation: 4 },
  buttonDisabled: { backgroundColor: '#818CF8', shadowOpacity: 0 },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  errorContainer: { marginTop: 24, padding: 16, backgroundColor: '#FEF2F2', borderRadius: 12, borderWidth: 1, borderColor: '#FCA5A5' },
  errorText: { color: '#EF4444', fontSize: 16, fontWeight: '700', textAlign: 'center', marginBottom: 12 },
  logHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#FECACA' },
  logTitle: { fontSize: 14, color: '#991B1B', fontWeight: '600' },
  logBox: { backgroundColor: '#111827', padding: 12, borderRadius: 8, marginTop: 8 },
  logItem: { color: '#34D399', fontFamily: 'Courier', fontSize: 11, marginBottom: 4 },
});
