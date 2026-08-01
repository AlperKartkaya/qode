import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { verifyNumber } from '../utils/api';

export default function NumberVerifyScreen({ navigation }) {
  const [phoneNumber, setPhoneNumber] = useState('+905390000020');
  const [loading, setLoading] = useState(false);

  const handleVerify = async () => {
    setLoading(true);
    try {
      // In reality, this would initiate the OIDC Auth Flow first
      const result = await verifyNumber(phoneNumber);
      if (result.devicePhoneNumberVerified) {
        navigation.replace('Home', { phoneNumber });
      } else {
        Alert.alert('Verification Failed', 'Number could not be verified over the cellular network.');
      }
    } catch (error) {
      Alert.alert('Error', 'An error occurred during verification.');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>VERIFY YOUR NUMBER</Text>
      <Text style={styles.subtitle}>Open Gateway Number Verification</Text>
      
      <TextInput
        style={styles.input}
        value={phoneNumber}
        onChangeText={setPhoneNumber}
        keyboardType="phone-pad"
        placeholder="Phone Number"
      />
      
      {loading ? (
        <ActivityIndicator size="large" color="#0000ff" />
      ) : (
        <Button title="Sign In" onPress={handleVerify} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 20, backgroundColor: '#f5f5f5' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 10, textAlign: 'center' },
  subtitle: { fontSize: 16, marginBottom: 30, textAlign: 'center', color: '#666' },
  input: { borderWidth: 1, borderColor: '#ccc', padding: 10, marginBottom: 20, borderRadius: 5, backgroundColor: '#fff' },
});
