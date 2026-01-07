import { Amplify } from 'aws-amplify';

const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_ZaGim7F6D',
      userPoolClientId: '2c8l8faf7tmdtkbqvkb7d93afb',
      region: 'us-east-1'
    }
  }
};

Amplify.configure(awsConfig);

export default awsConfig;